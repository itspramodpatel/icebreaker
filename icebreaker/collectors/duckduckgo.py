"""DuckDuckGo search collector - no API key needed. Uses ddgs library."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from ddgs import DDGS

from ..config import Config
from ..models import CollectorResult, ResolvedIdentity, SearchResult
from . import register
from .base import AbstractCollector

logger = logging.getLogger(__name__)


def _sync_search(query: str, max_results: int) -> list[dict]:
    """Run DDG search synchronously (library doesn't support async)."""
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


@register
class DuckDuckGoCollector(AbstractCollector):
    name = "duckduckgo"

    @classmethod
    def check_available(cls, config: Config) -> bool:
        return True

    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        all_results: list[SearchResult] = []

        try:
            # Start with resolver's queries (already include company/location context)
            queries = list(identity.search_queries)

            name = identity.full_name or identity.raw_input
            # Add social/professional discovery queries
            extra = [
                f"{name} linkedin profile",
                f"{name} linkedin posts",
                f"{name} twitter OR x.com posts",
                f"{name} instagram",
                f"{name} youtube channel",
                f"{name} about biography hobbies interests",
                f"{name} blog OR medium OR substack",
                f"{name} speaker OR conference OR interview",
                f"{name} podcast OR webinar",
                f"{name} quotes OR opinions",
            ]
            # If we have a LinkedIn URL, search for their posts specifically
            if identity.linkedin_url or identity.usernames:
                slug = identity.usernames[0] if identity.usernames else ""
                if slug:
                    extra.append(f"site:linkedin.com {slug} posts")
                    extra.append(f"linkedin.com/posts/{slug}")
            # Only add extras that aren't redundant with existing queries
            for q in extra:
                if q not in queries:
                    queries.append(q)

            # If we have an email, also search the full name without quotes
            if identity.email and identity.full_name:
                queries.append(identity.full_name)

            # Run searches (in thread pool since library is sync)
            loop = asyncio.get_event_loop()
            max_per_query = min(self.config.max_search_results, 10)

            for query in queries:
                try:
                    raw_results = await loop.run_in_executor(
                        None, partial(_sync_search, query, max_per_query)
                    )
                    for item in raw_results:
                        all_results.append(
                            SearchResult(
                                title=item.get("title", ""),
                                url=item.get("href", ""),
                                snippet=item.get("body", ""),
                                source="duckduckgo",
                            )
                        )
                    logger.info(f"DDG query '{query}': {len(raw_results)} results")
                except Exception as e:
                    logger.warning(f"DDG query '{query}' failed: {e}")
                    continue

            # Deduplicate by URL
            seen_urls: set[str] = set()
            deduped: list[SearchResult] = []
            for r in all_results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    deduped.append(r)

            logger.info(f"DDG total: {len(deduped)} unique results")
            return CollectorResult(source=self.name, success=True, results=deduped)

        except Exception as e:
            logger.exception("DuckDuckGo search failed")
            return CollectorResult(source=self.name, success=False, error=str(e))
