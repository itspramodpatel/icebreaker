"""Direct profile collector for explicit social profile URLs."""

from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

from ..config import Config
from ..models import CollectorResult, ResolvedIdentity, SearchResult
from . import register
from .base import AbstractCollector

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_profile_text(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "lxml")

    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""

    meta_parts: list[str] = []
    for key in ("description", "og:description", "twitter:description"):
        tag = soup.find("meta", attrs={"name": key}) or soup.find(
            "meta", attrs={"property": key}
        )
        if tag and tag.get("content"):
            meta_parts.append(_clean_text(tag["content"]))

    structured_parts: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("name", "headline", "description", "jobTitle", "worksFor"):
                value = item.get(key)
                if isinstance(value, dict):
                    value = value.get("name", "")
                if isinstance(value, str) and value.strip():
                    structured_parts.append(_clean_text(value))

    heading_parts = [
        _clean_text(tag.get_text(" ", strip=True))
        for tag in soup.find_all(["h1", "h2"], limit=8)
        if tag.get_text(strip=True)
    ]

    content_parts = []
    if title:
        content_parts.append(f"Title: {title}")
    if meta_parts:
        content_parts.append("Meta: " + " | ".join(dict.fromkeys(meta_parts)))
    if structured_parts:
        content_parts.append("Structured data: " + " | ".join(dict.fromkeys(structured_parts)))
    if heading_parts:
        content_parts.append("Headings: " + " | ".join(dict.fromkeys(heading_parts)))

    snippet = meta_parts[0] if meta_parts else title
    content = "\n".join(content_parts)[:5000]
    return title, snippet, content


@register
class DirectProfileCollector(AbstractCollector):
    name = "direct_profile"

    @classmethod
    def check_available(cls, config: Config) -> bool:
        return True

    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        urls: list[str] = []
        if identity.linkedin_url:
            urls.append(identity.linkedin_url)
        if identity.twitter_handle:
            urls.append(f"https://x.com/{identity.twitter_handle}")

        results: list[SearchResult] = []
        for url in urls:
            try:
                resp = await self.client.get(url, headers=HEADERS, follow_redirects=True, timeout=10.0)
                if resp.status_code != 200:
                    logger.debug("Direct profile fetch failed for %s with status %s", url, resp.status_code)
                    continue
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                title, snippet, content = _extract_profile_text(resp.text)
                if not any((title, snippet, content)):
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        content=content,
                        source="direct_profile",
                    )
                )
            except Exception as exc:
                logger.debug("Direct profile fetch failed for %s: %s", url, exc)

        return CollectorResult(source=self.name, success=True, results=results)
