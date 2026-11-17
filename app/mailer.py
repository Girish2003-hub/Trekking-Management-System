import re
import smtplib
from email.message import EmailMessage
from html import unescape

from flask import current_app


def send_email(to, subject, html):
    message = EmailMessage()
    message["From"] = current_app.config["MAIL_SENDER"]
    message["To"] = to
    message["Subject"] = subject

    plain_text = re.sub(r"</(?:td|th)>", " | ", html, flags=re.IGNORECASE)
    plain_text = re.sub(r"<br\s*/?>|</(?:p|tr|li|h[1-6])>", "\n", plain_text, flags=re.IGNORECASE)
    plain_text = unescape(re.sub(r"<[^>]*>", "", plain_text))
    message.set_content(plain_text.strip() or "This message contains an HTML report.")
    message.add_alternative(html, subtype="html")

    with smtplib.SMTP(
        current_app.config["MAIL_SERVER"],
        current_app.config["MAIL_PORT"],
        timeout=10,
    ) as smtp:
        smtp.send_message(message)
