"""Google Search collector - uses SerpAPI or Google Custom Search Engine."""

from __future__ import annotations

import logging

from ..config import Config
from ..models import CollectorResult, ResolvedIdentity, SearchResult
from . import register
from .base import AbstractCollector

logger = logging.getLogger(__name__)


@register
class GoogleSearchCollector(AbstractCollector):
    name = "google_search"

    @classmethod
    def check_available(cls, config: Config) -> bool:
        return config.has_serpapi() or config.has_google_cse()

    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        try:
            if self.config.has_serpapi():
                return await self._search_serpapi(identity)
            elif self.config.has_google_cse():
                return await self._search_google_cse(identity)
            else:
                return CollectorResult(
                    source=self.name, success=False, error="No search API key configured"
                )
        except Exception as e:
            logger.exception("Google search failed")
            return CollectorResult(source=self.name, success=False, error=str(e))

    async def _search_serpapi(self, identity: ResolvedIdentity) -> CollectorResult:
        all_results: list[SearchResult] = []

        for query in identity.search_queries:
            resp = await self.client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.config.serpapi_key,
                    "engine": "google",
                    "num": self.config.max_search_results,
                    "gl": "us",
                    "hl": "en",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("organic_results", []):
                all_results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="google_serpapi",
                        date=item.get("date"),
                    )
                )

            # Also grab knowledge graph if present
            kg = data.get("knowledge_graph", {})
            if kg:
                all_results.append(
                    SearchResult(
                        title=kg.get("title", ""),
                        url=kg.get("website", ""),
                        snippet=kg.get("description", ""),
                        content=str(kg),
                        source="google_knowledge_graph",
                    )
                )

            # Social profiles from search
            for profile in data.get("social_profiles", []):
                all_results.append(
                    SearchResult(
                        title=profile.get("name", ""),
                        url=profile.get("link", ""),
                        snippet=f"Social profile: {profile.get('name', '')}",
                        source="google_social_profile",
                    )
                )

        return CollectorResult(source=self.name, success=True, results=all_results)

    async def _search_google_cse(self, identity: ResolvedIdentity) -> CollectorResult:
        all_results: list[SearchResult] = []

        for query in identity.search_queries:
            resp = await self.client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "q": query,
                    "key": self.config.google_cse_key,
                    "cx": self.config.google_cse_id,
                    "num": min(self.config.max_search_results, 10),  # CSE max is 10
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                all_results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="google_cse",
                    )
                )

        return CollectorResult(source=self.name, success=True, results=all_results)
