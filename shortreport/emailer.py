import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import SmtpConfig


def send_email(config: SmtpConfig, subject: str, body: str) -> None:
    if not all([config.user, config.password, config.from_email, config.to_email]):
        raise RuntimeError("Missing SMTP_USER/SMTP_APP_PASSWORD/FROM_EMAIL/TO_EMAIL")

    msg = MIMEMultipart()
    msg["From"] = config.from_email
    msg["To"] = config.to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL(config.host, config.port) as server:
        server.login(config.user, config.password)
        server.send_message(msg)
