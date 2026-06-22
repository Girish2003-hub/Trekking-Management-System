from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_

from app.decorators import role_required
from app.extensions import db
from app.models import Booking, Trek


user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/dashboard")
@login_required
@role_required("user")
def dashboard():
    difficulty = request.args.get("difficulty", "").strip()
    location = request.args.get("location", "").strip()

    filters = [Trek.status.in_(["approved", "open"])]
    if difficulty:
        filters.append(Trek.difficulty == difficulty)
    if location:
        filters.append(Trek.location.ilike(f"%{location}%"))

    available_treks = Trek.query.filter(and_(*filters)).order_by(Trek.start_date.asc()).all()
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()

    return render_template(
        "user/dashboard.html",
        treks=available_treks,
        bookings=my_bookings,
        selected_difficulty=difficulty,
        location=location,
    )


@user_bp.route("/book/<int:trek_id>", methods=["POST"])
@login_required
@role_required("user")
def book_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if not trek:
        flash("Trek not found.", "danger")
        return redirect(url_for("user.dashboard"))

    if trek.status != "open":
        flash("Booking allowed only for Open treks.", "danger")
        return redirect(url_for("user.dashboard"))

    if trek.available_slots <= 0:
        flash("No slots available for this trek.", "danger")
        return redirect(url_for("user.dashboard"))

    existing = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status="booked").first()
    if existing:
        flash("You already booked this trek.", "warning")
        return redirect(url_for("user.dashboard"))

    booking = Booking(user_id=current_user.id, trek_id=trek.id, status="booked")
    trek.available_slots -= 1

    db.session.add(booking)
    db.session.commit()

    flash("Trek booked successfully.", "success")
    return redirect(url_for("user.dashboard"))


@user_bp.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
@role_required("user")
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first()
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("user.history"))

    if booking.status != "booked":
        flash("Only booked treks can be cancelled.", "warning")
        return redirect(url_for("user.history"))

    trek = booking.trek
    booking.status = "cancelled"

    if trek and trek.status in {"approved", "open"} and trek.available_slots < trek.total_slots:
        trek.available_slots += 1

    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(url_for("user.history"))


@user_bp.route("/history")
@login_required
@role_required("user")
def history():
    records = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template("user/history.html", records=records)


@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("user")
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.contact = request.form.get("contact", current_user.contact).strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("user.profile"))

    return render_template("user/profile.html")
