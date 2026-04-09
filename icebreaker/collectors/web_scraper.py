"""Web scraper collector - fetches and extracts text from discovered URLs."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..config import Config
from ..models import CollectorResult, ResolvedIdentity, SearchResult
from . import register
from .base import AbstractCollector

logger = logging.getLogger(__name__)

# Domains worth scraping for personal/professional info
PRIORITY_DOMAINS = {
    "linkedin.com",
    "twitter.com",
    "x.com",
    "github.com",
    "medium.com",
    "about.me",
    "crunchbase.com",
    "angel.co",
    "wellfound.com",
    "substack.com",
    "wordpress.com",
    "blogger.com",
    "youtube.com",
    "instagram.com",
    "facebook.com",
    "reddit.com",
    "quora.com",
    "slideshare.net",
    "speakerdeck.com",
}

# Domains to skip (paywalls, sign-in walls, etc.)
SKIP_DOMAINS = {
    "google.com",
    "googleapis.com",
    "serpapi.com",
    "bing.com",
    "yahoo.com",
    "duckduckgo.com",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_text(html: str, max_length: int = 5000) -> str:
    """Extract readable text from HTML, focusing on main content."""
    soup = BeautifulSoup(html, "lxml")

    # Remove script, style, nav, footer, header
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title_text = soup.title.get_text(" ", strip=True) if soup.title else ""

    meta_parts = []
    for key in ("description", "og:description", "twitter:description"):
        tag = soup.find("meta", attrs={"name": key}) or soup.find(
            "meta", attrs={"property": key}
        )
        if tag and tag.get("content"):
            meta_parts.append(tag.get("content", "").strip())

    heading_parts = [
        tag.get_text(" ", strip=True)
        for tag in soup.find_all(["h1", "h2", "h3"], limit=12)
        if tag.get_text(strip=True)
    ]

    # Try to find main content areas
    main = soup.find("main") or soup.find("article") or soup.find(id="content")
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    parts = []
    if title_text:
        parts.append(f"Title: {title_text}")
    if meta_parts:
        parts.append("Meta: " + " | ".join(dict.fromkeys(meta_parts)))
    if heading_parts:
        parts.append("Headings: " + " | ".join(dict.fromkeys(heading_parts)))
    if text:
        parts.append(text)

    return "\n".join(parts)[:max_length]


def _extract_meta(html: str) -> dict:
    """Extract meta tags (description, og:title, etc.)."""
    soup = BeautifulSoup(html, "lxml")
    meta = {}

    for tag in soup.find_all("meta"):
        name = tag.get("name", "") or tag.get("property", "")
        content = tag.get("content", "")
        if name and content:
            meta[name.lower()] = content

    return meta


def _score_url(url: str) -> int:
    """Score a URL for relevance - higher is better."""
    domain = urlparse(url).netloc.lower().replace("www.", "")
    score = 0
    if any(d in domain for d in PRIORITY_DOMAINS):
        score += 10
    # About/bio pages are high value
    path = urlparse(url).path.lower()
    if any(kw in path for kw in ["/about", "/bio", "/profile", "/speaker", "/author"]):
        score += 5
    return score


@register
class WebScraperCollector(AbstractCollector):
    name = "web_scraper"

    @classmethod
    def check_available(cls, config: Config) -> bool:
        return True  # Always available, no API key needed

    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        """Scrape the top URLs from prior collector results.

        This collector is meant to run AFTER google_search, using URLs
        discovered there. It's passed URLs via identity.search_queries
        won't have them yet, so the pipeline feeds URLs separately.
        """
        # The pipeline will call scrape_urls directly
        return CollectorResult(source=self.name, success=True, results=[])

    async def scrape_urls(self, urls: list[str]) -> CollectorResult:
        """Scrape a list of URLs and extract text content."""
        results: list[SearchResult] = []

        # Score and sort URLs, take top N
        scored = sorted(urls, key=_score_url, reverse=True)
        to_scrape = scored[: self.config.scrape_max_pages]

        for url in to_scrape:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            if any(d in domain for d in SKIP_DOMAINS):
                continue

            try:
                resp = await self.client.get(
                    url, headers=HEADERS, follow_redirects=True, timeout=10.0
                )
                if resp.status_code != 200:
                    continue
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                html = resp.text
                text = _extract_text(html)
                meta = _extract_meta(html)

                if len(text) < 50:
                    continue

                results.append(
                    SearchResult(
                        title=meta.get("og:title", meta.get("title", "")),
                        url=url,
                        snippet=meta.get("description", meta.get("og:description", "")),
                        content=text,
                        source=f"web_scrape:{domain}",
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to scrape {url}: {e}")
                continue

        return CollectorResult(source=self.name, success=True, results=results)
