"""Deterministic test fixtures. Never call live network or model providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from privacyradar.hashing import doc_hash, section_hashes

FIXTURE_NAMESPACE = UUID("8f14e45f-ea52-4c2a-9e1d-0b3c6a7d9e01")
FROZEN_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
EXAMPLE_EMAIL_DOMAIN = "example.test"


def stable_uuid(*parts: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, ":".join(parts))


@dataclass(frozen=True)
class CompanyFixture:
    id: UUID
    slug: str
    name: str
    website: str
    category: str
    created_at: datetime


@dataclass(frozen=True)
class SourceFixture:
    id: UUID
    company_id: UUID
    kind: str
    url: str
    region: str
    enabled: bool
    crawl_delay_s: int


@dataclass(frozen=True)
class ObservationFixture:
    id: UUID
    source_id: UUID
    fetched_at: datetime
    http_status: int | None
    content_type: str
    raw_html: str
    markdown: str
    doc_hash: str
    section_hashes: dict[str, str]
    fetch_error: str | None
    region: str
    resolved_url: str


@dataclass(frozen=True)
class ClaimFixture:
    id: UUID
    observation_id: UUID
    model: str
    practices: dict[str, object]
    created_at: datetime


@dataclass(frozen=True)
class UserFixture:
    id: UUID
    handle: str
    region: str
    email: str
    created_at: datetime


@dataclass(frozen=True)
class FollowFixture:
    id: UUID
    user_id: UUID
    company_id: UUID
    status: str
    created_at: datetime


@dataclass(frozen=True)
class NotificationFixture:
    id: UUID
    user_id: UUID
    event_id: UUID
    channel: str
    state: str
    created_at: datetime


def make_company(
    *,
    slug: str = "signal",
    name: str = "Signal",
    website: str = "https://signal.org",
    category: str = "messaging",
    clock: datetime = FROZEN_NOW,
) -> CompanyFixture:
    return CompanyFixture(
        id=stable_uuid("company", slug),
        slug=slug,
        name=name,
        website=website,
        category=category,
        created_at=clock,
    )


def make_source(
    company: CompanyFixture,
    *,
    kind: str = "privacy",
    region: str = "global",
    url: str | None = None,
    enabled: bool = True,
    crawl_delay_s: int = 2,
) -> SourceFixture:
    policy_url = url or f"https://fixtures.privacyradar.test/{company.slug}/privacy"
    return SourceFixture(
        id=stable_uuid("source", str(company.id), kind, region),
        company_id=company.id,
        kind=kind,
        url=policy_url,
        region=region,
        enabled=enabled,
        crawl_delay_s=crawl_delay_s,
    )


def make_observation(
    source: SourceFixture,
    *,
    markdown: str = "# Privacy\nWe collect your email address to create an account.\n",
    html: str = "<h1>Privacy</h1><p>We collect your email address to create an account.</p>",
    status: int | None = 200,
    content_type: str = "text/html",
    fetch_error: str | None = None,
    clock: datetime = FROZEN_NOW,
) -> ObservationFixture:
    digest = doc_hash(markdown)
    return ObservationFixture(
        id=stable_uuid("observation", str(source.id), digest),
        source_id=source.id,
        fetched_at=clock,
        http_status=status,
        content_type=content_type,
        raw_html=html,
        markdown=markdown,
        doc_hash=digest,
        section_hashes=section_hashes(markdown) if markdown else {},
        fetch_error=fetch_error,
        region=source.region,
        resolved_url=source.url,
    )


def make_claim(
    observation: ObservationFixture,
    company: CompanyFixture,
    *,
    model: str = "fake-model",
    clock: datetime = FROZEN_NOW,
) -> ClaimFixture:
    quote = "We collect your email address to create an account."
    practices: dict[str, object] = {
        "company": company.name,
        "practices": [
            {
                "party": "first",
                "data_types": ["email"],
                "purposes": ["product"],
                "collection_mode": "user_provided",
                "third_parties": [],
                "retention": "unspecified",
                "user_control": "unspecified",
                "quotes": [{"text": quote, "section": "Privacy"}],
            }
        ],
        "notes": "",
    }
    return ClaimFixture(
        id=stable_uuid("claim", str(observation.id), model),
        observation_id=observation.id,
        model=model,
        practices=practices,
        created_at=clock,
    )


def make_user(
    *,
    handle: str = "signal-tester",
    region: str = "US",
    clock: datetime = FROZEN_NOW,
) -> UserFixture:
    email = f"{handle}@{EXAMPLE_EMAIL_DOMAIN}"
    return UserFixture(
        id=stable_uuid("user", handle),
        handle=handle,
        region=region,
        email=email,
        created_at=clock,
    )


def make_follow(
    user: UserFixture,
    company: CompanyFixture,
    *,
    status: str = "active",
    clock: datetime = FROZEN_NOW,
) -> FollowFixture:
    return FollowFixture(
        id=stable_uuid("follow", str(user.id), str(company.id)),
        user_id=user.id,
        company_id=company.id,
        status=status,
        created_at=clock,
    )


def make_notification(
    user: UserFixture,
    *,
    event_id: UUID | None = None,
    channel: str = "email",
    state: str = "pending",
    clock: datetime = FROZEN_NOW,
) -> NotificationFixture:
    resolved_event = event_id or stable_uuid("event", "seed-change")
    return NotificationFixture(
        id=stable_uuid("notification", str(user.id), str(resolved_event), channel),
        user_id=user.id,
        event_id=resolved_event,
        channel=channel,
        state=state,
        created_at=clock,
    )
