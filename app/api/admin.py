"""Admin endpoints: treks, staff, users, bookings, search, statistics."""
import re
from collections import Counter

from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import func

from app.api import api_bp
from app.api.helpers import (
    DIFFICULTIES, TREK_STATUSES, clear_trek_cache, error, parse_date, parse_int, trek_json, user_json,
)
from app.decorators import role_required
from app.extensions import db
from app.models import Booking, StaffProfile, Trek, User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXTRA_TREK_FIELDS = ("description", "price", "instructions")  # used only if your Trek model has them


# ---------------------------------------------------------------- statistics

@api_bp.get("/admin/stats")
@role_required("admin")
def admin_stats():
    treks = Trek.query.all()
    bookings = Booking.query.all()

    participants_per_trek = Counter()
    bookings_per_month = Counter()
    for b in bookings:
        bookings_per_month[b.booking_date.strftime("%Y-%m")] += 1
        if b.status in ("booked", "completed"):
            participants_per_trek[b.trek.name] += b.participants

    return jsonify({
        "counts": {
            "treks": len(treks),
            "users": User.query.filter_by(role="user").count(),
            "staff": User.query.filter_by(role="staff").count(),
            "bookings": len(bookings),
            "active_bookings": sum(b.status == "booked" for b in bookings),
            "completed_treks": sum(t.status == "completed" for t in treks),
            "pending_treks": sum(t.status == "pending" for t in treks),
        },
        "charts": {
            "popular_treks": participants_per_trek.most_common(5),
            "treks_by_status": Counter(t.status for t in treks),
            "treks_by_difficulty": Counter(t.difficulty.lower() for t in treks),
            "bookings_by_status": Counter(b.status for b in bookings),
            "bookings_per_month": sorted(bookings_per_month.items())[-12:],
        },
    })


# ---------------------------------------------------------------- treks

def _trek_or_404(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        error("Trek not found", 404)
    return trek


def _apply_trek_fields(trek, data, creating):
    """Validate the body and copy it onto trek. Used by both create and update."""
    name = (data.get("name") or "").strip()
    location = (data.get("location") or "").strip()
    difficulty = (data.get("difficulty") or "").strip().lower()
    if not 3 <= len(name) <= 120:
        error("Trek name must be 3-120 characters")
    if not 2 <= len(location) <= 120:
        error("Location must be 2-120 characters")
    if difficulty not in DIFFICULTIES:
        error("Difficulty must be easy, moderate or hard")

    duplicate = Trek.query.filter(func.lower(Trek.name) == name.lower(), Trek.id != (trek.id or 0)).first()
    if duplicate:
        error("A trek with this name already exists", 409)

    start = parse_date(data.get("start_date"), "start_date")
    end = parse_date(data.get("end_date"), "end_date")
    if end < start:
        error("End date cannot be before start date")
    total = parse_int(data.get("total_slots"), "total_slots", minimum=1)

    booked = 0 if creating else (
        db.session.query(func.coalesce(func.sum(Booking.participants), 0))
        .filter(Booking.trek_id == trek.id, Booking.status.in_(("booked", "completed"))).scalar()
    )
    if total < booked:
        error(f"{booked} people are already booked; total slots cannot go below that")

    trek.name, trek.location, trek.difficulty = name, location, difficulty
    trek.start_date, trek.end_date = start, end
    trek.duration_days = (end - start).days + 1  # duration is derived, so it can't disagree with the dates
    trek.total_slots = total
    trek.available_slots = total - booked
    for field in EXTRA_TREK_FIELDS:
        if hasattr(Trek, field) and field in data:
            setattr(trek, field, data[field])


@api_bp.get("/admin/treks")
@role_required("admin")
def admin_list_treks():
    """All treks including history. ?q=&status=&difficulty="""
    query = Trek.query
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(Trek.name.ilike(f"%{q}%") | Trek.location.ilike(f"%{q}%"))
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("difficulty"):
        query = query.filter(func.lower(Trek.difficulty) == request.args["difficulty"].lower())
    treks = query.order_by(Trek.start_date.desc()).all()
    return jsonify({"treks": [trek_json(t) for t in treks]})


@api_bp.post("/admin/treks")
@role_required("admin")
def admin_create_trek():
    data = request.get_json(silent=True) or {}
    trek = Trek(status="pending", created_by_admin_id=current_user.id)
    _apply_trek_fields(trek, data, creating=True)
    db.session.add(trek)
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek created", "trek": trek_json(trek)}), 201


@api_bp.put("/admin/treks/<int:trek_id>")
@role_required("admin")
def admin_update_trek(trek_id):
    trek = _trek_or_404(trek_id)
    if trek.status == "completed":
        error("Completed treks are kept as history and cannot be edited")
    _apply_trek_fields(trek, request.get_json(silent=True) or {}, creating=False)
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek updated", "trek": trek_json(trek)})


@api_bp.patch("/admin/treks/<int:trek_id>/status")
@role_required("admin")
def admin_set_trek_status(trek_id):
    """Body: {"status": "approved"} - admin may set any status (e.g. approve a pending trek)."""
    trek = _trek_or_404(trek_id)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in TREK_STATUSES:
        error("Unknown status")
    if status == "open" and trek.assigned_staff_id is None:
        error("Assign a staff member before opening the trek")
    trek.status = status
    if status == "completed":
        Booking.query.filter_by(trek_id=trek.id, status="booked").update({"status": "completed"})
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": f"Trek status set to {status}", "trek": trek_json(trek)})


@api_bp.put("/admin/treks/<int:trek_id>/assign")
@role_required("admin")
def admin_assign_staff(trek_id):
    """Body: {"staff_id": 5} or {"staff_id": null} to unassign."""
    trek = _trek_or_404(trek_id)
    staff_id = (request.get_json(silent=True) or {}).get("staff_id")
    if staff_id is None:
        trek.assigned_staff_id = None
    else:
        staff = db.session.get(User, parse_int(staff_id, "staff_id", minimum=1))
        if staff is None or staff.role != "staff":
            error("Staff member not found", 404)
        if staff.is_blacklisted or not staff.is_approved:
            error("This staff member is deactivated or blacklisted")
        trek.assigned_staff_id = staff.id
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Staff assignment saved", "trek": trek_json(trek)})


@api_bp.delete("/admin/treks/<int:trek_id>")
@role_required("admin")
def admin_delete_trek(trek_id):
    trek = _trek_or_404(trek_id)
    if Booking.query.filter_by(trek_id=trek.id).count():
        # Deleting would erase users' trekking history, which the spec says to keep.
        error("This trek has bookings; close it instead of deleting so history is kept", 409)
    db.session.delete(trek)
    db.session.commit()
    clear_trek_cache()
    return jsonify({"message": "Trek deleted"})


# ---------------------------------------------------------------- staff

def _staff_json(user):
    data = user_json(user)
    profile = user.staff_profile
    data.update({
        "phone": profile.phone if profile else None,
        "experience_years": profile.experience_years if profile else 0,
        "specialization": profile.specialization if profile else None,
        "assigned_treks": [{"id": t.id, "name": t.name, "status": t.status} for t in user.staff_treks],
    })
    return data


@api_bp.get("/admin/staff")
@role_required("admin")
def admin_list_staff():
    query = User.query.filter_by(role="staff")
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(User.name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    return jsonify({"staff": [_staff_json(u) for u in query.order_by(User.name).all()]})


@api_bp.post("/admin/staff")
@role_required("admin")
def admin_create_staff():
    """Admin is the only way a staff account can exist (no staff registration)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not 2 <= len(name) <= 120:
        error("Name must be 2-120 characters")
    if not EMAIL_RE.match(email):
        error("Enter a valid email")
    if len(password) < 6:
        error("Password must be at least 6 characters")
    if User.query.filter_by(email=email).first():
        error("This email is already registered", 409)

    staff = User(name=name, email=email, role="staff", is_approved=True, is_blacklisted=False,
                 contact=(data.get("contact") or "").strip() or None)
    staff.set_password(password)
    db.session.add(staff)
    db.session.flush()  # gives staff.id before commit
    db.session.add(StaffProfile(
        user_id=staff.id,
        phone=(data.get("phone") or "").strip() or None,
        experience_years=parse_int(data.get("experience_years", 0), "experience_years"),
        specialization=(data.get("specialization") or "").strip() or None,
    ))
    db.session.commit()
    return jsonify({"message": "Staff member created", "staff": _staff_json(staff)}), 201


@api_bp.put("/admin/staff/<int:user_id>")
@role_required("admin")
def admin_update_staff(user_id):
    staff = db.session.get(User, user_id)
    if staff is None or staff.role != "staff":
        error("Staff member not found", 404)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or staff.name).strip()
    if not 2 <= len(name) <= 120:
        error("Name must be 2-120 characters")
    staff.name = name
    staff.contact = (data.get("contact") or "").strip() or None
    profile = staff.staff_profile or StaffProfile(user_id=staff.id)
    profile.phone = (data.get("phone") or "").strip() or None
    profile.experience_years = parse_int(data.get("experience_years", 0), "experience_years")
    profile.specialization = (data.get("specialization") or "").strip() or None
    db.session.add(profile)
    db.session.commit()
    return jsonify({"message": "Staff member updated", "staff": _staff_json(staff)})


# ---------------------------------------------------------------- users

@api_bp.get("/admin/users")
@role_required("admin")
def admin_list_users():
    query = User.query.filter_by(role="user")
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(User.name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    users = query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        data = user_json(u)
        data["booking_count"] = len(u.bookings)
        result.append(data)
    return jsonify({"users": result})


@api_bp.patch("/admin/accounts/<int:user_id>")
@role_required("admin")
def admin_set_account_status(user_id):
    """Users and staff. Body: {"action": "activate"|"deactivate"|"blacklist"|"unblacklist"}"""
    account = db.session.get(User, user_id)
    if account is None or account.role == "admin":
        error("Account not found", 404)
    action = (request.get_json(silent=True) or {}).get("action")
    if action == "activate":
        account.is_approved = True
    elif action == "deactivate":
        account.is_approved = False
    elif action == "blacklist":
        account.is_blacklisted = True
    elif action == "unblacklist":
        account.is_blacklisted = False
    else:
        error("action must be activate, deactivate, blacklist or unblacklist")

    if account.role == "staff":
        if account.staff_profile:
            account.staff_profile.status = (
                "blacklisted" if account.is_blacklisted else "active" if account.is_approved else "inactive"
            )
        if action in ("deactivate", "blacklist"):
            # A blocked staff member must not keep managing treks.
            for trek in account.staff_treks:
                if trek.status not in ("completed",):
                    trek.assigned_staff_id = None
            clear_trek_cache()
    db.session.commit()
    return jsonify({"message": f"Account {action}d", "account": user_json(account)})


# ---------------------------------------------------------------- bookings & search

@api_bp.get("/admin/bookings")
@role_required("admin")
def admin_list_bookings():
    """Every booking ever made. ?status=&trek_id="""
    query = Booking.query
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if (request.args.get("trek_id") or "").isdigit():
        query = query.filter_by(trek_id=int(request.args["trek_id"]))
    bookings = query.order_by(Booking.booking_date.desc()).all()
    return jsonify({"bookings": [
        dict(b.to_dict(), user_name=b.trekker.name, user_email=b.trekker.email) for b in bookings
    ]})


@api_bp.get("/admin/search")
@role_required("admin")
def admin_search():
    """GET /api/admin/search?q=text&type=all|users|staff|treks"""
    q = (request.args.get("q") or "").strip()
    kind = request.args.get("type", "all")
    if len(q) < 1:
        error("Type something to search")
    like = f"%{q}%"
    result = {}
    if kind in ("all", "users", "staff"):
        people = User.query.filter(User.role != "admin", User.name.ilike(like) | User.email.ilike(like)).all()
        if kind in ("all", "users"):
            result["users"] = [user_json(u) for u in people if u.role == "user"]
        if kind in ("all", "staff"):
            result["staff"] = [_staff_json(u) for u in people if u.role == "staff"]
    if kind in ("all", "treks"):
        treks = Trek.query.filter(Trek.name.ilike(like) | Trek.location.ilike(like)).all()
        result["treks"] = [trek_json(t) for t in treks]
    return jsonify(result)
