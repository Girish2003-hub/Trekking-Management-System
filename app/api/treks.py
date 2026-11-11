"""Public trek catalogue: list, search, filter, detail. Cached in Redis."""
from flask import jsonify, request
from sqlalchemy import func

from app.api import api_bp
from app.api.helpers import PUBLIC_STATUSES, TREK_CACHE_PREFIX, error, trek_json
from app.cache import cache_get, cache_set
from app.extensions import db
from app.models import Trek


@api_bp.get("/treks")
def list_treks():
    """GET /api/treks?q=&difficulty=&location=&min_days=&max_days=&status=

    Only approved/open treks are shown. Every distinct filter combination
    gets its own cache key, e.g. "treks:list:difficulty=easy&q=".
    """
    args = {k: (request.args.get(k) or "").strip() for k in
            ("q", "difficulty", "location", "min_days", "max_days", "status")}
    cache_key = TREK_CACHE_PREFIX + "list:" + "&".join(f"{k}={v}" for k, v in sorted(args.items()))

    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify({"treks": cached, "cached": True})

    query = Trek.query.filter(Trek.status.in_(PUBLIC_STATUSES))
    if args["status"] in PUBLIC_STATUSES:
        query = query.filter(Trek.status == args["status"])
    if args["q"]:
        like = f"%{args['q']}%"
        query = query.filter(Trek.name.ilike(like) | Trek.location.ilike(like))
    if args["difficulty"]:
        # lower() on both sides: V1 data stored "Hard", V2 stores "hard".
        query = query.filter(func.lower(Trek.difficulty) == args["difficulty"].lower())
    if args["location"]:
        query = query.filter(Trek.location.ilike(f"%{args['location']}%"))
    if args["min_days"].isdigit():
        query = query.filter(Trek.duration_days >= int(args["min_days"]))
    if args["max_days"].isdigit():
        query = query.filter(Trek.duration_days <= int(args["max_days"]))

    treks = [trek_json(t) for t in query.order_by(Trek.start_date).all()]
    cache_set(cache_key, treks)
    return jsonify({"treks": treks, "cached": False})


@api_bp.get("/treks/<int:trek_id>")
def get_trek(trek_id):
    cache_key = f"{TREK_CACHE_PREFIX}detail:{trek_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify({"trek": cached, "cached": True})

    trek = db.session.get(Trek, trek_id)
    if trek is None or trek.status not in PUBLIC_STATUSES:
        error("Trek not found", 404)
    data = trek_json(trek)
    cache_set(cache_key, data)
    return jsonify({"trek": data, "cached": False})
