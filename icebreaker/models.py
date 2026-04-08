"""Core data models for IceBreaker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class InputType(Enum):
    EMAIL = "email"
    LINKEDIN_URL = "linkedin_url"
    FULL_NAME = "full_name"
    TWITTER_URL = "twitter_url"
    GENERIC_URL = "generic_url"


@dataclass
class ResolvedIdentity:
    """Normalized input with all known identifiers."""

    raw_input: str
    input_type: InputType
    full_name: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    usernames: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """A single search result or scraped item."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    content: str = ""
    source: str = ""
    date: str | None = None


@dataclass
class CollectorResult:
    """Output from one collector."""

    source: str
    success: bool
    results: list[SearchResult] = field(default_factory=list)
    error: str | None = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProfileData:
    """Aggregated profile from all collectors."""

    identity: ResolvedIdentity
    collector_results: list[CollectorResult] = field(default_factory=list)

    def all_results(self) -> list[SearchResult]:
        """Flatten all search results across collectors."""
        out = []
        for cr in self.collector_results:
            if cr.success:
                out.extend(cr.results)
        return out


@dataclass
class MeetingBrief:
    """Final synthesized output."""

    subject_name: str
    professional_summary: str
    personal_interests: list[str]
    conversation_starters: list[str]
    recent_activity: list[str]
    key_topics: list[str]
    warnings: list[str]
    sources_used: list[str]
    # New deeper profile fields
    social_presence: dict = field(default_factory=dict)
    personality_traits: list[str] = field(default_factory=list)
    values_and_causes: list[str] = field(default_factory=list)
    content_they_share: list[str] = field(default_factory=list)
    communication_style: str = ""
    raw_json: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)
