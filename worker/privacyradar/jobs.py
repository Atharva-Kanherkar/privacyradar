"""ARQ worker. Per-source jobs; crawl_all is no longer the failure domain."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from privacyradar.db import connect
from privacyradar.leases import drain_once, schedule_due_sources
from privacyradar.retry import HTTP_CONCURRENCY
from privacyradar.settings import settings


async def schedule_due_job(ctx: dict[str, Any]) -> int:
    def _run() -> int:
        with connect() as conn:
            count = schedule_due_sources(conn, datetime.now(UTC))
            conn.commit()
            return count

    return await asyncio.to_thread(_run)


async def fetch_due_job(ctx: dict[str, Any]) -> list[str]:
    def _run() -> list[str]:
        with connect() as conn:
            results = drain_once(conn)
            conn.commit()
            return results

    return await asyncio.to_thread(_run)


class WorkerSettings:
    functions = [schedule_due_job, fetch_due_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [
        cron(schedule_due_job, hour={0, 6, 12, 18}, minute=20),
        cron(fetch_due_job, hour={0, 6, 12, 18}, minute=25),
    ]
    max_jobs = HTTP_CONCURRENCY
