"""Small Redis cache helper.

Values are stored as JSON strings with an expiry (TTL). If Redis is not
running, every function quietly does nothing, so the app still works
(it just reads from SQLite every time).
"""
import json

from flask import current_app

from app import extensions


def _client():
    return extensions.redis_client


def cache_get(key):
    try:
        raw = _client().get(key)
    except Exception:
        return None
    return json.loads(raw) if raw else None


def cache_set(key, value, ttl=None):
    ttl = ttl or current_app.config["CACHE_TTL_SECONDS"]
    try:
        _client().setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete_prefix(prefix):
    """Delete every key that starts with prefix, e.g. 'treks:'."""
    try:
        for key in _client().scan_iter(match=prefix + "*"):
            _client().delete(key)
    except Exception:
        pass
