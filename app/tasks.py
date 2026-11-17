import csv
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape

from celery_worker import celery
from flask import current_app

from app.extensions import db
from app.mailer import send_email
from app.models import Booking, Trek, User


@celery.task(name="app.tasks.export_bookings_csv")
def export_bookings_csv(user_id):
    user = db.session.get(User, user_id)
    if user is None or user.role != "user":
        raise ValueError(f"Trekker account {user_id} was not found")

    bookings = (
        Booking.query.filter_by(user_id=user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    os.makedirs(current_app.config["EXPORT_DIR"], exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"bookings_{user.id}_{timestamp}.csv"
    filepath = os.path.join(current_app.config["EXPORT_DIR"], filename)

    with open(filepath, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "User ID",
            "Trek Name",
            "Location",
            "Booking Status",
            "Booking Date",
            "Start Date",
            "End Date",
        ])
        for booking in bookings:
            data = booking.to_dict()
            writer.writerow([
                data["user_id"],
                data["trek_name"],
                data["location"],
                data["status"],
                data["booking_date"],
                data["start_date"],
                data["end_date"],
            ])

    send_email(
        user.email,
        "Your trekking booking history export is ready",
        (
            f"<html><body><p>Hello {escape(user.name)},</p>"
            f"<p>Your booking history CSV export is ready: "
            f"<strong>{escape(filename)}</strong>.</p>"
            "<p>The file is available in the application's exports folder.</p>"
            "</body></html>"
        ),
    )
    return filename


@celery.task(name="app.tasks.send_daily_reminders")
def send_daily_reminders():
    reminder_date = date.today() + timedelta(days=1)
    bookings = (
        Booking.query.join(Trek)
        .join(User, Booking.user_id == User.id)
        .filter(
            Booking.status == "booked",
            Trek.start_date == reminder_date,
            User.role == "user",
            User.is_approved.is_(True),
            User.is_blacklisted.is_(False),
        )
        .order_by(User.id, Trek.start_date, Trek.name)
        .all()
    )

    user_bookings = defaultdict(list)
    for booking in bookings:
        user_bookings[booking.user_id].append(booking)

    for upcoming_bookings in user_bookings.values():
        user = upcoming_bookings[0].trekker
        rows = "".join(
            "<tr>"
            f"<td>{escape(booking.trek.name)}</td>"
            f"<td>{escape(booking.trek.location)}</td>"
            f"<td>{booking.trek.start_date.isoformat()}</td>"
            "</tr>"
            for booking in upcoming_bookings
        )
        send_email(
            user.email,
            "Reminder: your trek starts tomorrow",
            (
                f"<html><body><p>Hello {escape(user.name)},</p>"
                "<p>This is a reminder about your upcoming trek:</p>"
                "<table><thead><tr><th>Trek</th><th>Location</th>"
                f"<th>Start date</th></tr></thead><tbody>{rows}</tbody></table>"
                "<p>Please arrive prepared, bring suitable gear and follow your "
                "trek staff's safety instructions.</p></body></html>"
            ),
        )
    return len(user_bookings)


@celery.task(name="app.tasks.send_monthly_activity_report")
def send_monthly_activity_report():
    first_of_this_month = date.today().replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    completed_treks = Trek.query.filter(
        Trek.status == "completed",
        Trek.end_date >= last_month_start,
        Trek.end_date <= last_month_end,
    ).order_by(Trek.name).all()
    trek_ids = [trek.id for trek in completed_treks]
    completed_bookings = []
    if trek_ids:
        completed_bookings = Booking.query.filter(
            Booking.trek_id.in_(trek_ids),
            Booking.status == "completed",
        ).all()

    participant_count = sum(booking.participants for booking in completed_bookings)
    user_count = len({booking.user_id for booking in completed_bookings})
    participants_by_trek = Counter()
    for booking in completed_bookings:
        participants_by_trek[booking.trek.name] += booking.participants

    popular_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{count}</td></tr>"
        for name, count in participants_by_trek.most_common(5)
    )
    if not popular_rows:
        popular_rows = "<tr><td colspan='2'>No completed bookings</td></tr>"

    admin = User.query.filter_by(role="admin").order_by(User.id).first()
    if admin is None:
        raise ValueError("Cannot send the monthly report because no admin account exists")
    report_html = (
        "<html><body>"
        f"<h1>Trekking activity report: {last_month_start:%B %Y}</h1>"
        f"<p>Treks conducted: {len(completed_treks)}</p>"
        f"<p>Participants: {participant_count}</p>"
        f"<p>Unique users participated: {user_count}</p>"
        "<h2>Popular treks (participants)</h2>"
        "<table><thead><tr><th>Trek</th><th>Participants</th></tr></thead>"
        f"<tbody>{popular_rows}</tbody></table>"
        "</body></html>"
    )
    send_email(
        admin.email,
        f"Monthly trekking activity report: {last_month_start:%B %Y}",
        report_html,
    )
    return {
        "treks_conducted": len(completed_treks),
        "participants": participant_count,
        "unique_users": user_count,
    }
