"""All JSON endpoints live under /api.

Each later step adds one module (treks.py, bookings.py, staff.py, admin.py)
and imports it at the bottom of this file so its routes attach to api_bp.
"""
from flask import Blueprint, jsonify

from app import extensions

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health():
    """Quick check that Flask is up and whether Redis is reachable."""
    try:
        redis_ok = bool(extensions.redis_client.ping())
    except Exception:
        redis_ok = False
    return jsonify({"status": "ok", "redis": redis_ok})


# Importing these modules runs their @api_bp.get/post decorators, which attaches
# their routes to api_bp. They are at the bottom to avoid a circular import.
from app.api import treks, user, staff, admin  # noqa: E402,F401

# ---------------------------------------------------------------------------
# YOUR PART - authentication (the spec does not allow AI to write this).
# The Vue frontend (static/js/store.js) expects these JSON endpoints:
#   POST /api/auth/login     {email, password}        -> 200 {"user": {...}} | 401 {"message"}
#   POST /api/auth/register  {name, email, password, contact}  -> 201 {"user": {...}}
#   POST /api/auth/logout                             -> 200
#   GET  /api/auth/me                                 -> 200 {"user": {...}} | 401
# "user" should be helpers.user_json(user) so it contains "role".
# If you use token auth instead of cookies, return {"token": ...} from login and
# the frontend's api.js already sends it as "Authentication-Token" when present.
# ---------------------------------------------------------------------------
