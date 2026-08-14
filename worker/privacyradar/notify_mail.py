"""Email rendering, HMAC unsubscribe tokens, and delivery adapters."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any
from urllib.parse import quote

import httpx

from privacyradar.settings import settings

logger = logging.getLogger(__name__)

RESEND_API = "https://api.resend.com/emails"


class NotifyError(ValueError):
    """Notification configuration or token error."""


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def signing_secret() -> str:
    secret = settings.auth_secret or settings.notify_signing_key
    if not secret:
        raise NotifyError("missing_signing_secret")
    return secret


def fixture_delivery_enabled() -> bool:
    if os.environ.get("VERCEL_ENV") == "production":
        return False
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") == "production":
        return False
    return os.environ.get("AUTH_DELIVERY") == "fixture"


def public_base_url() -> str:
    return settings.public_base_url.rstrip("/")


def sign_unsub_token(
    *,
    user_id: str,
    purpose: str = "unsub",
    exp: int | None = None,
    secret: str | None = None,
) -> str:
    if "|" in user_id or "|" in purpose:
        raise NotifyError("invalid_token_field")
    expires = exp if exp is not None else int(datetime.now(UTC).timestamp()) + 90 * 24 * 3600
    payload = f"{user_id}|{purpose}|{expires}"
    body = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    key = (secret or signing_secret()).encode("utf-8")
    sig = hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_unsub_token(
    token: str, *, secret: str | None = None, now: datetime | None = None
) -> dict[str, str]:
    if token.count(".") != 1:
        raise NotifyError("invalid_token")
    body, sig = token.split(".", 1)
    key = (secret or signing_secret()).encode("utf-8")
    expected = hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise NotifyError("invalid_token")
    pad = "=" * (-len(body) % 4)
    try:
        payload = base64.urlsafe_b64decode(body + pad).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise NotifyError("invalid_token") from exc
    parts = payload.split("|")
    if len(parts) != 3:
        raise NotifyError("invalid_token")
    user_id, purpose, exp_raw = parts
    try:
        exp = int(exp_raw)
    except ValueError as exc:
        raise NotifyError("invalid_token") from exc
    stamp = now or datetime.now(UTC)
    if exp < int(stamp.timestamp()):
        raise NotifyError("expired_token")
    if purpose != "unsub" and not purpose.startswith("mute:"):
        raise NotifyError("invalid_token")
    return {"user_id": user_id, "purpose": purpose, "exp": str(exp)}


@dataclass(frozen=True)
class RenderedAlert:
    subject: str
    text: str
    html: str


def render_alert(
    *,
    company_name: str,
    headline: str,
    summary: str,
    event_id: str,
    kind: str,
    unsubscribe_token: str,
    data_types_added: list[str] | None = None,
) -> RenderedAlert:
    base = public_base_url()
    evidence = f"{base}/changes/{event_id}"
    settings_url = f"{base}/radar/settings"
    unsub = f"{base}/unsubscribe?token={quote(unsubscribe_token, safe='')}"
    added = ", ".join(data_types_added or []) or "their privacy practices"
    if kind == "correction":
        subject = f"Correction: earlier alert about {company_name}"
        why = (
            f"We corrected or rolled back a previously published alert about {company_name}. "
            "The earlier email should not be treated as current."
        )
        lead = f"An earlier PrivacyRadar alert about {company_name} was corrected."
    else:
        subject = f"Privacy change at {company_name}: {headline}"
        why = (
            f"This is a published, evidence-backed change to how {company_name} describes {added}."
        )
        lead = f"{company_name} published a material privacy-policy change."
    text = (
        f"{lead}\n\n"
        f"{headline}\n\n"
        f"{summary}\n\n"
        f"Why it matters: {why}\n\n"
        f"Evidence: {evidence}\n"
        f"Alert settings: {settings_url}\n"
        f"Unsubscribe: {unsub}\n"
    )
    html = (
        "<!doctype html><html lang='en'><body style='font-family:Georgia,serif;"
        "background:#f4efe6;color:#1c1917;padding:24px'>"
        f"<p>{escape(lead)}</p>"
        f"<h1 style='font-size:1.4rem'>{escape(headline)}</h1>"
        f"<p>{escape(summary)}</p>"
        f"<p>Why it matters: {escape(why)}</p>"
        f"<p><a href='{escape(evidence)}'>Read the evidence</a></p>"
        f"<p><a href='{escape(settings_url)}'>Alert settings</a></p>"
        f"<p><a href='{escape(unsub)}'>Unsubscribe</a></p>"
        "</body></html>"
    )
    if "<img" in html.lower() or "http-equiv" in html.lower():
        raise NotifyError("unsafe_html")
    return RenderedAlert(subject=subject, text=text, html=html)


@dataclass(frozen=True)
class SendResult:
    provider: str
    provider_message_id: str | None


class FakeProvider:
    def send(
        self,
        conn: Any,
        *,
        to_email: str,
        rendered: RenderedAlert,
        idempotency_key: str = "",
    ) -> SendResult:
        del idempotency_key
        conn.execute(
            """
            insert into notification_fixture_inbox (
              email_hash, subject, body_text, body_html
            )
            values (%s, %s, %s, %s)
            """,
            (email_hash(to_email), rendered.subject, rendered.text, rendered.html),
        )
        return SendResult(provider="fake", provider_message_id=None)


class ResendProvider:
    def send(
        self,
        conn: Any,
        *,
        to_email: str,
        rendered: RenderedAlert,
        idempotency_key: str = "",
    ) -> SendResult:
        del conn
        if settings.notify_provider != "resend":
            raise NotifyError("resend_disabled")
        if not settings.resend_api_key:
            raise NotifyError("missing_resend_key")
        if not idempotency_key:
            raise NotifyError("missing_idempotency_key")
        response = httpx.post(
            RESEND_API,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Idempotency-Key": idempotency_key,
            },
            json={
                "from": settings.notify_from,
                "to": [to_email],
                "subject": rendered.subject,
                "text": rendered.text,
                "html": rendered.html,
            },
            timeout=15.0,
        )
        if response.status_code >= 400:
            logger.warning("resend send failed", extra={"status": response.status_code})
            raise NotifyError("resend_failed")
        payload = response.json()
        message_id = payload.get("id") if isinstance(payload, dict) else None
        return SendResult(
            provider="resend",
            provider_message_id=str(message_id) if message_id else None,
        )


def get_provider() -> FakeProvider | ResendProvider:
    if settings.notify_provider == "resend":
        return ResendProvider()
    return FakeProvider()


def verify_svix_signature(
    *,
    secret: str,
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    now: datetime | None = None,
) -> None:
    stamp = now or datetime.now(UTC)
    try:
        ts = int(svix_timestamp)
    except ValueError as exc:
        raise NotifyError("invalid_webhook") from exc
    if abs(int(stamp.timestamp()) - ts) > 300:
        raise NotifyError("webhook_replay")
    raw_secret = secret
    if raw_secret.startswith("whsec_"):
        raw_secret = raw_secret[len("whsec_") :]
    try:
        key = base64.b64decode(raw_secret)
    except ValueError:
        key = raw_secret.encode("utf-8")
    signed = f"{svix_id}.{svix_timestamp}.".encode("ascii") + body
    digest = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode("ascii")
    candidates = [
        part.strip().removeprefix("v1,") if part.strip().startswith("v1,") else part.strip()
        for part in svix_signature.split(" ")
    ]
    if not any(hmac.compare_digest(digest, item) for item in candidates if item):
        raise NotifyError("invalid_webhook")


def parse_resend_webhook(body: bytes) -> dict[str, str]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise NotifyError("invalid_webhook") from exc
    if not isinstance(payload, dict):
        raise NotifyError("invalid_webhook")
    event_type = str(payload.get("type") or "")
    raw_data = payload.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    email_id = str(data.get("email_id") or data.get("id") or "")
    recipients = data.get("to") or []
    to_email = ""
    if isinstance(recipients, list) and recipients:
        first = recipients[0]
        if isinstance(first, str):
            to_email = first
        elif isinstance(first, dict):
            to_email = str(first.get("email") or "")
    elif isinstance(recipients, str):
        to_email = recipients
    return {"type": event_type, "email_id": email_id, "to": to_email}
