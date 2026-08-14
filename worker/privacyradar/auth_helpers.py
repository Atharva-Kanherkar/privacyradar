"""Consumer auth helpers mirrored by web/src/lib/auth-helpers.ts."""

from __future__ import annotations

import hashlib

FALLBACK_CALLBACK = "/account"


def safe_callback_url(raw: str | None) -> str:
    if not raw:
        return FALLBACK_CALLBACK
    if not raw.startswith("/") or raw.startswith("//"):
        return FALLBACK_CALLBACK
    if "://" in raw or "\\" in raw or "@" in raw:
        return FALLBACK_CALLBACK
    return raw


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
