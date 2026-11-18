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

# Authentication endpoints (/api/auth/login, register, logout, me) live in
# app/auth/routes.py on their own blueprint and use Flask-Login sessions.
