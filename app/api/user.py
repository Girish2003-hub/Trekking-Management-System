"""Trekker endpoints: book, cancel, pay (simulated), history, dashboard, profile."""
import os
import re
from datetime import date, datetime

from flask import current_app, jsonify, request, send_from_directory
from flask_login import current_user

from app.api import api_bp
from app.api.helpers import PUBLIC_STATUSES, clear_trek_cache, error, parse_int, trek_json, user_json
from app.decorators import role_required
from app.extensions import db
from app.models import Booking, Trek


def _my_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.user_id != current_user.id:
        error("Booking not found", 404)
    return booking


@api_bp.post("/bookings")
@role_required("user")
def create_booking():
    """Body: {"trek_id": 1, "participants": 2}

    Rules enforced here:
      1. trek must exist and be OPEN
      2. no second active booking by the same user for the same trek
      3. never book more than the available slots (no overbooking)
    """
    data = request.get_json(silent=True) or {}
    trek_id = parse_int(data.get("trek_id"), "trek_id", minimum=1)
    participants = parse_int(data.get("participants", 1), "participants", minimum=1)
    if participants > 10:
        error("You can book at most 10 participants at once")

    if current_user.is_blacklisted:
        error("Your account is blacklisted and cannot book treks", 403)

    trek = db.session.get(Trek, trek_id)
    if trek is None:
        error("Trek not found", 404)
    if trek.status != "open":
        error("Bookings are only allowed while the trek is Open")
    if trek.start_date < date.today():
        error("This trek has already started")

    duplicate = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status="booked").first()
    if duplicate:
        error("You have already booked this trek", 409)

    # Atomic slot decrement: the UPDATE only succeeds if enough slots remain at
    # that exact moment, so two people booking the last slot can't both win.
    updated = (
        Trek.query.filter(Trek.id == trek.id, Trek.available_slots >= participants)
        .update({Trek.available_slots: Trek.available_slots - participants}, synchronize_session=False)
    )
    if updated == 0:
        db.session.rollback()
        error("Not enough slots left for this trek", 409)

    booking = Booking(user_id=current_user.id, trek_id=trek.id, participants=participants)
    db.session.add(booking)
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek booked successfully", "booking": booking.to_dict()}), 201


@api_bp.patch("/bookings/<int:booking_id>/cancel")
@role_required("user")
def cancel_booking(booking_id):
    booking = _my_booking(booking_id)
    if booking.status != "booked":
        error("Only active bookings can be cancelled")
    if booking.trek.status in ("ongoing", "completed"):
        error("You cannot cancel after the trek has started")

    booking.status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    if booking.payment_status == "paid":
        booking.payment_status = "refunded"
    booking.trek.available_slots += booking.participants  # give the slots back
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Booking cancelled", "booking": booking.to_dict()})


@api_bp.post("/bookings/<int:booking_id>/pay")
@role_required("user")
def pay_booking(booking_id):
    """Payment simulation: no real gateway, just flips the status."""
    booking = _my_booking(booking_id)
    if booking.status != "booked":
        error("Only active bookings can be paid")
    if booking.payment_status == "paid":
        error("Already paid")
    booking.payment_status = "paid"
    db.session.commit()
    return jsonify({"message": "Payment successful (simulated)", "booking": booking.to_dict()})


@api_bp.get("/bookings")
@role_required("user")
def my_bookings():
    """Full trekking history of the logged-in user. ?status=booked|cancelled|completed"""
    query = Booking.query.filter_by(user_id=current_user.id)
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    bookings = query.order_by(Booking.booking_date.desc()).all()
    return jsonify({"bookings": [b.to_dict() for b in bookings]})


@api_bp.get("/user/dashboard")
@role_required("user")
def user_dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    active = [b for b in bookings if b.status == "booked"]
    upcoming = sorted(
        (b for b in active if b.trek.start_date >= date.today()),
        key=lambda b: b.trek.start_date,
    )
    available = (
        Trek.query.filter(Trek.status.in_(PUBLIC_STATUSES), Trek.start_date >= date.today())
        .order_by(Trek.start_date).limit(6).all()
    )
    return jsonify({
        "counts": {
            "total": len(bookings),
            "active": len(active),
            "completed": sum(b.status == "completed" for b in bookings),
            "cancelled": sum(b.status == "cancelled" for b in bookings),
        },
        "upcoming": [dict(b.to_dict(), trek_status=b.trek.status) for b in upcoming],
        "available_treks": [trek_json(t) for t in available],
    })


@api_bp.get("/user/profile")
@role_required("user", "staff", "admin")
def get_profile():
    return jsonify({"user": user_json(current_user)})


@api_bp.put("/user/profile")
@role_required("user", "staff", "admin")
def update_profile():
    """Body: {"name": "...", "contact": "..."}. Email/password belong to auth."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    contact = (data.get("contact") or "").strip()
    if not 2 <= len(name) <= 120:
        error("Name must be 2-120 characters")
    if contact and (not contact.lstrip("+").isdigit() or not 7 <= len(contact) <= 15):
        error("Contact must be 7-15 digits")
    current_user.name = name
    current_user.contact = contact or None
    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user_json(current_user)})


@api_bp.post("/user/export")
@role_required("user")
def export_booking_history():
    from kombu.exceptions import OperationalError

    from app.tasks import export_bookings_csv

    try:
        export_bookings_csv.delay(current_user.id)
    except OperationalError:
        current_app.logger.exception("Could not queue the booking history export")
        return jsonify({"message": "Export queue is unavailable. Please try again shortly."}), 503

    return jsonify({"message": "CSV export queued. You will receive an email when it is ready."}), 202


@api_bp.get("/user/exports/latest")
@api_bp.get("/user/exports/<filename>")
@role_required("user")
def download_export(filename=None):
    """Send one of the logged-in user's CSV exports (the newest one by default).

    Only names like bookings_<my id>_<timestamp>.csv are accepted, so a user can
    never download someone else's file or reach outside the exports folder.
    """
    export_dir = current_app.config["EXPORT_DIR"]
    pattern = re.compile(rf"^bookings_{current_user.id}_\d{{8}}T\d+Z\.csv$")

    if filename is None:
        mine = sorted(f for f in os.listdir(export_dir) if pattern.match(f)) if os.path.isdir(export_dir) else []
        if not mine:
            error("No export yet. Click 'Export history (CSV)' first.", 404)
        filename = mine[-1]  # timestamps sort in time order
    elif not pattern.match(filename) or not os.path.isfile(os.path.join(export_dir, filename)):
        error("Export not found", 404)

    return send_from_directory(export_dir, filename, as_attachment=True, mimetype="text/csv")
