from celery import Celery, Task
from celery.schedules import crontab

from app import create_app
from config import Config


flask_app = create_app()


class FlaskContextTask(Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery = Celery(
    "trekking_management",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)
celery.Task = FlaskContextTask
celery.conf.update(
    timezone=Config.CELERY_TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        "daily-trek-reminders": {
            "task": "app.tasks.send_daily_reminders",
            "schedule": crontab(hour=9, minute=0),
        },
        "monthly-trek-activity-report": {
            "task": "app.tasks.send_monthly_activity_report",
            "schedule": crontab(day_of_month=1, hour=9, minute=15),
        },
    },
)
