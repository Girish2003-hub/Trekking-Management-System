import os
from urllib.parse import quote


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # SQLite only (spec requirement). Tables are created in code by `flask init-db`.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "trekking.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis: used for caching here, and as the Celery broker/backend.
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
    REDIS_AUTH = f":{quote(REDIS_PASSWORD, safe='')}@" if REDIS_PASSWORD else ""
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_URL = os.environ.get("REDIS_URL", f"redis://{REDIS_AUTH}{REDIS_HOST}:6379/0")
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 300))

    # Celery uses Redis databases separate from the cache database.
    CELERY_BROKER_URL = os.environ.get(
        "CELERY_BROKER_URL", f"redis://{REDIS_AUTH}{REDIS_HOST}:6379/1"
    )
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", f"redis://{REDIS_AUTH}{REDIS_HOST}:6379/2"
    )
    CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", "Asia/Kolkata")

    # Mail for reminders / monthly report. MailHog on localhost:1025 works well for demos.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 1025))
    MAIL_SENDER = os.environ.get("MAIL_SENDER", "noreply@trek.local")

    # Where CSV exports are written.
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")
    # Used to build the download link in the "export ready" email.
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
