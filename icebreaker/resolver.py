"""Input resolver - detects input type and builds search queries."""

from __future__ import annotations

import re

from .models import InputType, ResolvedIdentity

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)")
TWITTER_RE = re.compile(r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)")


def _name_from_email(email: str) -> str | None:
    """Try to extract a name from an email address (e.g. john.doe@company.com -> John Doe)."""
    local = email.split("@")[0]
    # Common separators: . _ -
    parts = re.split(r"[._-]", local)
    # Filter out numeric parts and very short parts
    name_parts = [p.capitalize() for p in parts if p.isalpha() and len(p) > 1]
    if len(name_parts) >= 2:
        return " ".join(name_parts)
    return None


def _name_from_linkedin(slug: str) -> str | None:
    """Try to extract a name from a LinkedIn slug (e.g. jane-doe-123abc -> Jane Doe)."""
    # Remove trailing numbers/hashes
    clean = re.sub(r"-[0-9a-f]{4,}$", "", slug)
    parts = clean.split("-")
    name_parts = [p.capitalize() for p in parts if p.isalpha() and len(p) > 1]
    if name_parts:
        return " ".join(name_parts)
    return None


def _keywords_from_slug(slug: str) -> list[str]:
    """Extract useful name-like keywords from a LinkedIn slug."""
    clean = re.sub(r"-[0-9a-f]{4,}$", "", slug.lower())
    return [part for part in clean.split("-") if part.isalpha() and len(part) > 1]


def resolve(
    raw_input: str,
    name: str | None = None,
    email: str | None = None,
    company: str | None = None,
    location: str | None = None,
) -> ResolvedIdentity:
    """Detect the input type and build a ResolvedIdentity with search queries.

    Optional name/email/company/location params help disambiguate common names.
    """
    raw = raw_input.strip()
    identity = ResolvedIdentity(raw_input=raw, input_type=InputType.FULL_NAME)

    # Check if raw input is an email
    if EMAIL_RE.match(raw):
        identity.input_type = InputType.EMAIL
        identity.email = raw
        identity.full_name = name or _name_from_email(raw)
    # Check LinkedIn URL
    elif LINKEDIN_RE.search(raw):
        linkedin_match = LINKEDIN_RE.search(raw)
        identity.input_type = InputType.LINKEDIN_URL
        identity.linkedin_url = raw
        slug = linkedin_match.group(1)
        identity.usernames.append(slug)
        identity.full_name = name or _name_from_linkedin(slug)
    # Check Twitter URL
    elif TWITTER_RE.search(raw):
        twitter_match = TWITTER_RE.search(raw)
        identity.input_type = InputType.TWITTER_URL
        handle = twitter_match.group(1)
        identity.twitter_handle = handle
        identity.usernames.append(handle)
        identity.full_name = name
    else:
        # Treat as full name or freeform query
        identity.input_type = InputType.FULL_NAME
        identity.full_name = name or raw

    # Override with explicit params if provided
    if email:
        identity.email = email
    if name:
        identity.full_name = name

    # Build search queries — the more signals, the better
    identity.search_queries = _build_queries(identity, company, location)

    return identity


def _build_queries(
    identity: ResolvedIdentity,
    company: str | None = None,
    location: str | None = None,
) -> list[str]:
    """Build a list of search queries from all available signals."""
    queries = []
    name = identity.full_name
    email = identity.email

    # Email is the most unique identifier
    if email:
        queries.append(f'"{email}"')

    # Name + company is a strong disambiguator
    if name and company:
        queries.append(f'"{name}" "{company}"')
        queries.append(f'"{name}" {company} linkedin')

    # Name + location
    if name and location:
        queries.append(f'"{name}" {location}')

    # Name alone (less specific, but needed)
    if name:
        queries.append(f'"{name}"')

    # LinkedIn URL directly
    if identity.linkedin_url:
        slug = identity.usernames[0] if identity.usernames else ""
        if slug:
            queries.append(f"site:linkedin.com/in/{slug}")
            queries.append(f'"{slug}" linkedin')
            keywords = _keywords_from_slug(slug)
            if keywords:
                slug_name = " ".join(word.capitalize() for word in keywords)
                queries.append(f'"{slug_name}" linkedin')
                queries.append(f'"{slug_name}" profile')
                if company:
                    queries.append(f'"{slug_name}" "{company}" linkedin')
                if location:
                    queries.append(f'"{slug_name}" {location} linkedin')

    # Twitter handle
    if identity.twitter_handle:
        queries.append(f'"{identity.twitter_handle}" twitter')

    # If we have nothing specific, use raw input
    if not queries:
        queries.append(f'"{identity.raw_input}"')

    deduped = []
    seen = set()
    for query in queries:
        if query not in seen:
            seen.add(query)
            deduped.append(query)
    return deduped
