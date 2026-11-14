import logging
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from app.core.config import settings

log = logging.getLogger("app.email")


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    text: str


class EmailBackend(Protocol):
    async def send(self, email: OutgoingEmail) -> None: ...


class ConsoleBackend:
    async def send(self, email: OutgoingEmail) -> None:
        log.warning(
            "\n--- EMAIL (console backend) ---\nTo: %s\nSubject: %s\n\n%s\n---",
            email.to,
            email.subject,
            email.text,
        )


class MemoryBackend:
    """Keeps sent mails in memory — used by tests."""

    def __init__(self) -> None:
        self.outbox: list[OutgoingEmail] = []

    async def send(self, email: OutgoingEmail) -> None:
        self.outbox.append(email)


class SmtpBackend:
    """Any SMTP server: Brevo in production, Mailpit locally."""

    async def send(self, email: OutgoingEmail) -> None:
        import aiosmtplib

        msg = MimeMessage()
        msg["From"] = settings.email_from
        msg["To"] = email.to
        msg["Subject"] = email.subject
        msg.set_content(email.text)
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_starttls,
        )


def _build_backend() -> EmailBackend:
    match settings.email_backend:
        case "smtp":
            return SmtpBackend()
        case "memory":
            return MemoryBackend()
        case _:
            return ConsoleBackend()


email_backend: EmailBackend = _build_backend()


async def send_email(email: OutgoingEmail) -> None:
    try:
        await email_backend.send(email)
    except Exception:  # never break the request because of mail delivery
        log.exception("Failed to send e-mail to %s", email.to)
