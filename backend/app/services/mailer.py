"""Outbound email over SMTP, using only the standard library (no new
pip dependency) -- for "Email PO" (2026-09-12): real server-side send
with the PO PDF attached.

Unconfigured by default (see app/core/config.py): until backend/.env
carries real SMTP settings, send_email raises MailerNotConfigured so the
API returns a clear error instead of silently pretending to have sent
anything.
"""
import smtplib
from email.message import EmailMessage

from app.core.config import settings


class MailerNotConfigured(Exception):
    """No SMTP account has been set up yet."""


class MailerError(Exception):
    """SMTP accepted the settings but the send itself failed."""


def is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
    attachment_content_type: str = "application/pdf",
) -> None:
    if not is_configured():
        raise MailerNotConfigured(
            "Email sending is not configured yet. Add smtp_host / smtp_username / "
            "smtp_password / smtp_from_email to backend/.env -- see DEV_SETUP.md."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg.set_content(body_text)

    if attachment_bytes and attachment_filename:
        maintype, _, subtype = attachment_content_type.partition("/")
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=attachment_filename,
        )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as e:
        raise MailerError(f"Could not send email: {e}") from e
