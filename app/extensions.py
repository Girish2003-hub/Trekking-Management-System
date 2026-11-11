import redis
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

# Kept from V1 so your existing User model / user_loader still import.
# Replace or extend this when you write the V2 authentication.
login_manager = LoginManager()

# Created in create_app() once the config (REDIS_URL) is known.
redis_client = None


def init_redis(url):
    global redis_client
    redis_client = redis.Redis.from_url(url, decode_responses=True)
    return redis_client
