"""ARQ worker. Cron four times a day. Privacy pages do not need minute polling."""

from __future__ import annotations

import asyncio
from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from privacyradar.pipeline import crawl_all
from privacyradar.settings import settings


async def crawl_all_job(ctx: dict[str, Any]) -> list[str]:
    return await asyncio.to_thread(crawl_all)


class WorkerSettings:
    functions = [crawl_all_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [
        cron(crawl_all_job, hour={0, 6, 12, 18}, minute=20),
    ]
    max_jobs = 1
