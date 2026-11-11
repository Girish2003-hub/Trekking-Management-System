"""Trek staff endpoints. A staff member can only touch treks assigned to them."""
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import func

from app.api import api_bp
from app.api.helpers import clear_trek_cache, error, parse_int, trek_json
from app.decorators import role_required
from app.extensions import db
from app.models import Booking, Trek

# Status changes a staff member may make: current status -> allowed next statuses.
STAFF_TRANSITIONS = {
    "approved": {"open"},
    "open": {"closed", "ongoing"},
    "closed": {"open", "ongoing"},
    "ongoing": {"completed"},
}


def _assigned_trek(trek_id):
    """Return the trek only if the logged-in staff member is assigned to it."""
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        error("Trek not found", 404)
    if trek.assigned_staff_id != current_user.id:
        error("You are not assigned to this trek", 403)
    return trek


def _booked_people(trek_id):
    """Number of participants on active (or completed) bookings for a trek."""
    return db.session.query(func.coalesce(func.sum(Booking.participants), 0)).filter(
        Booking.trek_id == trek_id, Booking.status.in_(("booked", "completed"))
    ).scalar()


@api_bp.get("/staff/dashboard")
@role_required("staff")
def staff_dashboard():
    treks = Trek.query.filter_by(assigned_staff_id=current_user.id).order_by(Trek.start_date).all()
    data = [trek_json(t, booked_count=_booked_people(t.id)) for t in treks]
    return jsonify({
        "treks": data,
        "counts": {
            "assigned": len(treks),
            "open": sum(t.status == "open" for t in treks),
            "ongoing": sum(t.status == "ongoing" for t in treks),
            "completed": sum(t.status == "completed" for t in treks),
            "participants": sum(t["booked_count"] for t in data),
        },
    })


@api_bp.get("/staff/treks/<int:trek_id>")
@role_required("staff")
def staff_trek_detail(trek_id):
    trek = _assigned_trek(trek_id)
    bookings = Booking.query.filter_by(trek_id=trek.id).order_by(Booking.booking_date).all()
    participants = [
        dict(b.to_dict(), user_name=b.trekker.name, user_email=b.trekker.email, user_contact=b.trekker.contact)
        for b in bookings
    ]
    return jsonify({
        "trek": trek_json(trek, booked_count=_booked_people(trek.id)),
        "participants": participants,
        "allowed_statuses": sorted(STAFF_TRANSITIONS.get(trek.status, set())),
    })


@api_bp.patch("/staff/treks/<int:trek_id>")
@role_required("staff")
def staff_update_trek(trek_id):
    """Body: {"total_slots": 20} and/or {"status": "open" | "closed" | "ongoing" | "completed"}"""
    trek = _assigned_trek(trek_id)
    data = request.get_json(silent=True) or {}

    if "total_slots" in data:
        if trek.status in ("ongoing", "completed"):
            error("Slots cannot change once the trek has started")
        total = parse_int(data["total_slots"], "total_slots", minimum=1)
        booked = _booked_people(trek.id)
        if total < booked:
            error(f"{booked} people are already booked; total slots cannot go below that")
        trek.total_slots = total
        trek.available_slots = total - booked

    if "status" in data:
        new_status = data["status"]
        if new_status != trek.status:
            if new_status not in STAFF_TRANSITIONS.get(trek.status, set()):
                error(f"Cannot change status from {trek.status} to {new_status}")
            trek.status = new_status
            if new_status == "completed":
                # Everyone still booked has now completed the trek.
                Booking.query.filter_by(trek_id=trek.id, status="booked").update({"status": "completed"})

    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek updated", "trek": trek_json(trek, booked_count=_booked_people(trek.id))})


@api_bp.post("/staff/treks/<int:trek_id>/start")
@role_required("staff")
def staff_start_trek(trek_id):
    trek = _assigned_trek(trek_id)
    if trek.status not in ("open", "closed"):
        error("Only an Open or Closed trek can be started")
    trek.status = "ongoing"
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek marked as started", "trek": trek_json(trek)})


@api_bp.post("/staff/treks/<int:trek_id>/complete")
@role_required("staff")
def staff_complete_trek(trek_id):
    trek = _assigned_trek(trek_id)
    if trek.status != "ongoing":
        error("Start the trek before marking it completed")
    trek.status = "completed"
    Booking.query.filter_by(trek_id=trek.id, status="booked").update({"status": "completed"})
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek marked as completed", "trek": trek_json(trek)})


@api_bp.patch("/staff/bookings/<int:booking_id>")
@role_required("staff")
def staff_update_participant(booking_id):
    """Manage the participant list. Body: {"status": "cancelled" | "booked"}"""
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        error("Booking not found", 404)
    trek = _assigned_trek(booking.trek_id)
    if trek.status in ("ongoing", "completed"):
        error("Participants cannot be changed after the trek has started")

    new_status = (request.get_json(silent=True) or {}).get("status")
    if booking.status == "booked" and new_status == "cancelled":
        booking.status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        trek.available_slots += booking.participants
    elif booking.status == "cancelled" and new_status == "booked":
        if trek.available_slots < booking.participants:
            error("Not enough slots to restore this booking", 409)
        clash = Booking.query.filter_by(user_id=booking.user_id, trek_id=trek.id, status="booked").first()
        if clash:
            error("This user already has another active booking for this trek", 409)
        booking.status = "booked"
        booking.cancelled_at = None
        trek.available_slots -= booking.participants
    else:
        error("Allowed changes: booked -> cancelled, cancelled -> booked")

    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Participant updated", "booking": booking.to_dict()})
