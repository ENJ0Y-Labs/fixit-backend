import logging
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

def send_auth_email(*, to: str, subject: str, text: str) -> None:
    settings = get_settings()
    if not settings.mailgun_api_key or not settings.mailgun_domain:
        if settings.app_env.lower() in {"development", "test"}:
            logger.info("Auth email adapter is not configured; message suppressed for %s", to)
            return
        raise RuntimeError("Mailgun is required for authentication email delivery.")
    response = httpx.post(
        f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages",
        auth=("api", settings.mailgun_api_key),
        data={"from": settings.mailgun_from, "to": to, "subject": subject, "text": text},
        timeout=15.0,
    )
    response.raise_for_status()
