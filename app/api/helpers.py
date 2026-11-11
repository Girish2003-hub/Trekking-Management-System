"""Helpers shared by every API module: JSON conversion, input checks, cache keys."""
from datetime import date

from flask import abort, jsonify

from app.cache import cache_delete_prefix

DIFFICULTIES = ("easy", "moderate", "hard")
TREK_STATUSES = ("pending", "approved", "open", "closed", "ongoing", "completed")
# Treks a trekker is allowed to see in the catalogue.
PUBLIC_STATUSES = ("approved", "open")

TREK_CACHE_PREFIX = "treks:"


def error(message, code=400):
    """Stop the request and send {"message": ...} with an HTTP error code."""
    response = jsonify({"message": message})
    response.status_code = code
    abort(response)


def trek_json(trek, booked_count=None):
    data = {
        "id": trek.id,
        "name": trek.name,
        "location": trek.location,
        "difficulty": trek.difficulty,
        "duration_days": trek.duration_days,
        "total_slots": trek.total_slots,
        "available_slots": trek.available_slots,
        "status": trek.status,
        "start_date": trek.start_date.isoformat(),
        "end_date": trek.end_date.isoformat(),
        "assigned_staff_id": trek.assigned_staff_id,
        "assigned_staff_name": trek.assigned_staff.name if trek.assigned_staff else None,
    }
    # Optional extra fields: only included if your Trek model has them.
    for extra in ("description", "price", "instructions"):
        if hasattr(trek, extra):
            data[extra] = getattr(trek, extra)
    if booked_count is not None:
        data["booked_count"] = booked_count
    return data


def user_json(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "contact": user.contact,
        "is_active": bool(user.is_approved),
        "is_blacklisted": bool(user.is_blacklisted),
        "created_at": user.created_at.isoformat(),
    }


def parse_date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        error(f"{field} must be a date like 2026-12-31")


def parse_int(value, field, minimum=0):
    try:
        number = int(value)
    except (TypeError, ValueError):
        error(f"{field} must be a whole number")
    if number < minimum:
        error(f"{field} must be at least {minimum}")
    return number


def clear_trek_cache():
    """Call after ANY change to a trek, so users never see stale slots/status."""
    cache_delete_prefix(TREK_CACHE_PREFIX)
