import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # SQLite only (spec requirement). Tables are created in code by `flask init-db`.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "trekking.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis: used for caching here, and as the Celery broker/backend.
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 300))

    # Celery (you configure the worker/beat yourself).
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # Mail for reminders / monthly report. MailHog on localhost:1025 works well for demos.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 1025))
    MAIL_SENDER = os.environ.get("MAIL_SENDER", "noreply@trek.local")

    # Where CSV exports are written.
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")
