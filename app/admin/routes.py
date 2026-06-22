from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.decorators import role_required
from app.extensions import db
from app.models import Booking, Trek, User


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    trek_count = Trek.query.count()
    user_count = User.query.filter_by(role="user").count()
    staff_count = User.query.filter_by(role="staff").count()
    user_staff_count = user_count + staff_count
    booking_count = Booking.query.count()

    return render_template(
        "admin/dashboard.html",
        trek_count=trek_count,
        user_count=user_count,
        staff_count=staff_count,
        user_staff_count=user_staff_count,
        booking_count=booking_count,
    )


@admin_bp.route("/treks")
@login_required
@role_required("admin")
def treks():
    all_treks = Trek.query.order_by(Trek.start_date.asc()).all()
    return render_template("admin/treks.html", treks=all_treks)


@admin_bp.route("/treks/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_trek():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        difficulty = request.form.get("difficulty", "Easy").strip()
        duration_days = int(request.form.get("duration_days", 1))
        total_slots = int(request.form.get("total_slots", 1))
        start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

        trek = Trek(
            name=name,
            location=location,
            difficulty=difficulty,
            duration_days=duration_days,
            total_slots=total_slots,
            available_slots=total_slots,
            status="approved",
            start_date=start_date,
            end_date=end_date,
            created_by_admin_id=current_user.id,
        )

        db.session.add(trek)
        db.session.commit()
        flash("Trek created successfully.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", trek=None)


@admin_bp.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if not trek:
        flash("Trek not found.", "danger")
        return redirect(url_for("admin.treks"))

    if request.method == "POST":
        trek.name = request.form.get("name", "").strip()
        trek.location = request.form.get("location", "").strip()
        trek.difficulty = request.form.get("difficulty", "Easy").strip()
        trek.duration_days = int(request.form.get("duration_days", 1))

        new_total_slots = int(request.form.get("total_slots", trek.total_slots))
        booked_count = Booking.query.filter_by(trek_id=trek.id, status="booked").count()
        if new_total_slots < booked_count:
            flash("Total slots cannot be less than current booked users.", "danger")
            return render_template("admin/trek_form.html", trek=trek)

        trek.total_slots = new_total_slots
        trek.available_slots = new_total_slots - booked_count
        trek.status = request.form.get("status", trek.status)
        trek.start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        trek.end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

        if trek.status == "completed":
            Booking.query.filter_by(trek_id=trek.id, status="booked").update({"status": "completed"})
            trek.available_slots = 0

        db.session.commit()
        flash("Trek updated.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", trek=trek)


@admin_bp.route("/treks/<int:trek_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek:
        db.session.delete(trek)
        db.session.commit()
        flash("Trek deleted.", "success")
    return redirect(url_for("admin.treks"))


@admin_bp.route("/staff/approvals")
@login_required
@role_required("admin")
def staff_approvals():
    pending_staff = User.query.filter_by(role="staff", is_approved=False).all()
    approved_staff = User.query.filter_by(role="staff", is_approved=True).all()
    return render_template("admin/staff_approvals.html", pending_staff=pending_staff, approved_staff=approved_staff)


@admin_bp.route("/staff/<int:staff_id>/approve", methods=["POST"])
@login_required
@role_required("admin")
def approve_staff(staff_id):
    staff = db.session.get(User, staff_id)
    if staff and staff.role == "staff":
        staff.is_approved = True
        db.session.commit()
        flash("Staff approved.", "success")
    return redirect(url_for("admin.staff_approvals"))


@admin_bp.route("/staff/assign", methods=["GET", "POST"])
@login_required
@role_required("admin")
def assign_staff():
    staff_list = User.query.filter_by(role="staff", is_approved=True, is_blacklisted=False).all()
    trek_list = Trek.query.order_by(Trek.start_date.asc()).all()

    if request.method == "POST":
        staff_id = int(request.form.get("staff_id"))
        trek_id = int(request.form.get("trek_id"))

        trek = db.session.get(Trek, trek_id)
        staff = db.session.get(User, staff_id)

        if trek and staff and staff.role == "staff":
            trek.assigned_staff_id = staff.id
            db.session.commit()
            flash("Staff assigned to trek.", "success")

        return redirect(url_for("admin.assign_staff"))

    return render_template("admin/assign_staff.html", staff_list=staff_list, trek_list=trek_list)


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-blacklist", methods=["POST"])
@login_required
@role_required("admin")
def toggle_blacklist(user_id):
    user = db.session.get(User, user_id)
    if user and user.role != "admin":
        user.is_blacklisted = not user.is_blacklisted
        db.session.commit()
        flash("Blacklist status updated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-deactivate", methods=["POST"])
@login_required
@role_required("admin")
def toggle_deactivate(user_id):
    user = db.session.get(User, user_id)
    if user and user.role != "admin":
        user.is_approved = not user.is_approved
        db.session.commit()
        flash("Activation status updated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/bookings")
@login_required
@role_required("admin")
def bookings():
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings)


@admin_bp.route("/search")
@login_required
@role_required("admin")
def search():
    trek_q = request.args.get("trek_q", "").strip()
    staff_q = request.args.get("staff_q", "").strip()
    user_q = request.args.get("user_q", "").strip()
    active_tab = request.args.get("tab", "treks").strip().lower()
    if active_tab not in {"treks", "staff", "users"}:
        active_tab = "treks"

    users = []
    staff = []
    treks = []

    if trek_q:
        trek_filters = [Trek.name.ilike(f"%{trek_q}%"), Trek.location.ilike(f"%{trek_q}%")]
        if trek_q.isdigit():
            trek_filters.append(Trek.id == int(trek_q))
        treks = Trek.query.filter(or_(*trek_filters)).all()

    if staff_q:
        staff_filters = [User.name.ilike(f"%{staff_q}%"), User.email.ilike(f"%{staff_q}%")]
        if staff_q.isdigit():
            staff_filters.append(User.id == int(staff_q))
        staff = User.query.filter(User.role == "staff", or_(*staff_filters)).all()

    if user_q:
        user_filters = [User.name.ilike(f"%{user_q}%"), User.email.ilike(f"%{user_q}%")]
        if user_q.isdigit():
            user_filters.append(User.id == int(user_q))
        users = User.query.filter(User.role == "user", or_(*user_filters)).all()

    return render_template(
        "admin/search.html",
        users=users,
        staff=staff,
        treks=treks,
        active_tab=active_tab,
        trek_q=trek_q,
        staff_q=staff_q,
        user_q=user_q,
    )
