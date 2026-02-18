"""
Notification dispatcher — supports Telegram and email.
Configure via .env: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, or SMTP settings.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_notification(message: str, subject: str = "Career Tracker Alert") -> bool:
    """Send a notification via all configured channels."""
    sent = False
    if settings.telegram_bot_token and settings.telegram_chat_id:
        sent = await _send_telegram(message) or sent
    if settings.notify_email and settings.smtp_host:
        sent = _send_email(message, subject) or sent
    if not sent:
        logger.info(f"[notifier] No channels configured. Message: {message}")
    return sent


async def _send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info("[notifier] Telegram message sent")
            return True
    except Exception as e:
        logger.error(f"[notifier] Telegram send failed: {e}")
        return False


def _send_email(body: str, subject: str) -> bool:
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user or "career-tracker@localhost"
        msg["To"] = settings.notify_email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("[notifier] Email sent")
        return True
    except Exception as e:
        logger.error(f"[notifier] Email send failed: {e}")
        return False
