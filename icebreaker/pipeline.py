"""Pipeline orchestrator - runs collectors and aggregates results."""

from __future__ import annotations

import asyncio
import logging

import httpx

from .collectors import get_available_collectors
from .collectors.web_scraper import WebScraperCollector
from .config import Config
from .models import ProfileData, ResolvedIdentity

logger = logging.getLogger(__name__)


async def run_pipeline(identity: ResolvedIdentity, config: Config) -> ProfileData:
    """Run all available collectors and aggregate results."""
    profile = ProfileData(identity=identity)

    async with httpx.AsyncClient(
        timeout=config.request_timeout, follow_redirects=True
    ) as client:
        # Phase 1: Run search collectors (Google, etc.)
        collector_classes = get_available_collectors(config)
        search_collectors = [
            cls for cls in collector_classes if cls.name != "web_scraper"
        ]

        logger.info(
            f"Running {len(search_collectors)} search collectors: "
            f"{[c.name for c in search_collectors]}"
        )

        tasks = [cls(config, client).collect(identity) for cls in search_collectors]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in search_results:
            if isinstance(result, Exception):
                logger.error(f"Collector failed: {result}")
            else:
                profile.collector_results.append(result)

        # Phase 2: Scrape URLs discovered by search collectors
        urls = []
        seen = set()

        direct_urls = [identity.linkedin_url]
        if identity.twitter_handle:
            direct_urls.append(f"https://x.com/{identity.twitter_handle}")
        for url in direct_urls:
            if url and url not in seen:
                urls.append(url)
                seen.add(url)

        for cr in profile.collector_results:
            if cr.success:
                for sr in cr.results:
                    if sr.url and sr.url not in seen:
                        urls.append(sr.url)
                        seen.add(sr.url)

        if urls:
            logger.info(f"Scraping {min(len(urls), config.scrape_max_pages)} URLs")
            scraper = WebScraperCollector(config, client)
            scrape_result = await scraper.scrape_urls(urls)
            profile.collector_results.append(scrape_result)

    total = len(profile.all_results())
    logger.info(f"Pipeline complete: {total} total results from {len(profile.collector_results)} collectors")
    return profile
