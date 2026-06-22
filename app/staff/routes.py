from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from app.decorators import role_required
from app.extensions import db
from app.models import Booking, Trek


staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.before_request
@login_required
@role_required("staff")
def ensure_staff_access():
    if not current_user.is_approved:
        logout_user()
        flash("Your staff account is pending admin approval.", "warning")
        return redirect(url_for("auth.login"))

    if current_user.is_blacklisted:
        logout_user()
        flash("Your account is blacklisted. Contact admin.", "danger")
        return redirect(url_for("auth.login"))


@staff_bp.route("/dashboard")
@login_required
@role_required("staff")
def dashboard():
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).order_by(Trek.start_date.asc()).all()
    counts = {trek.id: Booking.query.filter_by(trek_id=trek.id, status="booked").count() for trek in assigned_treks}
    return render_template("staff/dashboard.html", treks=assigned_treks, counts=counts)


@staff_bp.route("/trek/<int:trek_id>", methods=["GET", "POST"])
@login_required
@role_required("staff")
def trek_detail(trek_id):
    trek = db.session.get(Trek, trek_id)
    if not trek or trek.assigned_staff_id != current_user.id:
        flash("You can only manage treks assigned to you.", "danger")
        return redirect(url_for("staff.dashboard"))

    if request.method == "POST":
        new_status = request.form.get("status", trek.status).strip().lower()

        new_slots_raw = request.form.get("available_slots", str(trek.available_slots)).strip()
        try:
            new_slots = int(new_slots_raw)
        except ValueError:
            flash("Available slots must be a valid number.", "danger")
            return redirect(url_for("staff.trek_detail", trek_id=trek.id))

        if new_status not in {"open", "closed", "started", "completed"}:
            flash("Invalid trek status.", "danger")
            return redirect(url_for("staff.trek_detail", trek_id=trek.id))

        booked_count = Booking.query.filter_by(trek_id=trek.id, status="booked").count()
        max_allowed = trek.total_slots - booked_count
        if new_slots < 0 or new_slots > max_allowed:
            flash("Available slots value is invalid.", "danger")
            return redirect(url_for("staff.trek_detail", trek_id=trek.id))

        trek.available_slots = new_slots
        trek.status = new_status

        if new_status == "completed":
            Booking.query.filter_by(trek_id=trek.id, status="booked").update({"status": "completed"})
            trek.available_slots = 0

        db.session.commit()
        flash("Trek details updated.", "success")
        return redirect(url_for("staff.trek_detail", trek_id=trek.id))

    participants = Booking.query.filter_by(trek_id=trek.id).order_by(Booking.booking_date.desc()).all()
    return render_template("staff/trek_detail.html", trek=trek, participants=participants)


@staff_bp.route("/trek/<int:trek_id>/participant/<int:booking_id>/status", methods=["POST"])
@login_required
@role_required("staff")
def update_participant_status(trek_id, booking_id):
    trek = db.session.get(Trek, trek_id)
    if not trek or trek.assigned_staff_id != current_user.id:
        flash("You can only manage participants for your assigned treks.", "danger")
        return redirect(url_for("staff.dashboard"))

    booking = Booking.query.filter_by(id=booking_id, trek_id=trek.id).first()
    if not booking:
        flash("Participant booking not found.", "danger")
        return redirect(url_for("staff.trek_detail", trek_id=trek.id))

    new_status = request.form.get("booking_status", "").strip().lower()
    if new_status not in {"booked", "cancelled", "completed"}:
        flash("Invalid participant status.", "danger")
        return redirect(url_for("staff.trek_detail", trek_id=trek.id))

    if booking.status == new_status:
        flash("Participant status is unchanged.", "info")
        return redirect(url_for("staff.trek_detail", trek_id=trek.id))

    if booking.status == "booked" and new_status == "cancelled":
        if trek.available_slots < trek.total_slots:
            trek.available_slots += 1
    elif booking.status == "cancelled" and new_status == "booked":
        if trek.status.lower() != "open" or trek.available_slots <= 0:
            flash("Cannot move to booked: trek is not open or has no slots.", "danger")
            return redirect(url_for("staff.trek_detail", trek_id=trek.id))
        trek.available_slots -= 1

    booking.status = new_status
    db.session.commit()
    flash("Participant status updated.", "success")
    return redirect(url_for("staff.trek_detail", trek_id=trek.id))
