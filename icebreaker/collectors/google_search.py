"""Google Search collector - uses SerpAPI, SearchAPI, or Google CSE."""

from __future__ import annotations

import logging

import httpx

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
        return config.has_serpapi() or config.has_searchapi() or config.has_google_cse()

    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        try:
            if self.config.has_serpapi():
                return await self._search_serpapi(identity)
            elif self.config.has_searchapi():
                return await self._search_searchapi(identity)
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

        try:
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
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                return CollectorResult(
                    source=self.name,
                    success=False,
                    error="SerpAPI returned 401 Unauthorized. Check or replace ICEBREAKER_SERPAPI_KEY.",
                )
            raise

        return CollectorResult(source=self.name, success=True, results=all_results)

    async def _search_searchapi(self, identity: ResolvedIdentity) -> CollectorResult:
        all_results: list[SearchResult] = []

        try:
            for query in identity.search_queries:
                resp = await self.client.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": self.config.searchapi_key,
                        "gl": "us",
                        "hl": "en",
                        "page": 1,
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
                            source="google_searchapi",
                            date=item.get("date"),
                        )
                    )

                knowledge_graph = data.get("knowledge_graph", {})
                if knowledge_graph:
                    all_results.append(
                        SearchResult(
                            title=knowledge_graph.get("title", ""),
                            url=knowledge_graph.get("website", ""),
                            snippet=knowledge_graph.get("description", ""),
                            content=str(knowledge_graph),
                            source="google_knowledge_graph",
                        )
                    )

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                return CollectorResult(
                    source=self.name,
                    success=False,
                    error="SearchAPI returned 401 Unauthorized. Check or replace ICEBREAKER_SEARCHAPI_KEY.",
                )
            raise

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
