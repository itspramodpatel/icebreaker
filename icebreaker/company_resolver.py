"""Resolver for company and opportunity research mode."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import CompanyResolvedIdentity

LINKEDIN_COMPANY_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/company/([a-zA-Z0-9_-]+)"
)


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def _website_domain(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain or None


def resolve_company(
    company_name: str,
    website: str | None = None,
    linkedin_company_url: str | None = None,
    geography: str | None = None,
    industry: str | None = None,
    target_roles: list[str] | None = None,
    event_focus: str | None = None,
    services: str | None = None,
) -> CompanyResolvedIdentity:
    """Build a normalized company identity and focused search queries."""
    name = company_name.strip()
    website = _normalize_url(website)
    linkedin_company_url = _normalize_url(linkedin_company_url)
    roles = [role.strip() for role in (target_roles or []) if role.strip()]

    identity = CompanyResolvedIdentity(
        raw_input=name,
        company_name=name,
        website=website,
        linkedin_company_url=linkedin_company_url,
        geography=geography.strip() if geography else None,
        industry=industry.strip() if industry else None,
        target_roles=roles,
        event_focus=event_focus.strip() if event_focus else None,
        services=services.strip() if services else None,
    )
    identity.search_queries = _build_company_queries(identity)
    return identity


def _build_company_queries(identity: CompanyResolvedIdentity) -> list[str]:
    name = identity.company_name
    queries = [
        f'"{name}" official site',
        f'"{name}" marketing',
        f'"{name}" brand',
        f'"{name}" leadership',
        f'"{name}" executive team',
        f'"{name}" marketing team',
        f'"{name}" campaign',
        f'"{name}" partnership',
        f'"{name}" press release',
        f'"{name}" event',
        f'"{name}" exhibition',
        f'"{name}" trade show',
        f'"{name}" experiential',
        f'"{name}" hiring marketing',
        f'site:linkedin.com/company "{name}"',
        f'site:linkedin.com/in "{name}" CMO',
        f'site:linkedin.com/in "{name}" "Chief Marketing Officer"',
        f'site:linkedin.com/in "{name}" "Marketing Director"',
        f'site:linkedin.com/in "{name}" "Brand Director"',
        f'site:linkedin.com/in "{name}" "Brand Manager"',
        f'site:linkedin.com/in "{name}" "Event Director"',
        f'site:linkedin.com/in "{name}" "Event Manager"',
    ]

    if identity.geography:
        queries.extend(
            [
                f'"{name}" {identity.geography} marketing',
                f'"{name}" {identity.geography} event',
            ]
        )

    if identity.industry:
        queries.extend(
            [
                f'"{name}" {identity.industry}',
                f'"{name}" {identity.industry} campaign',
                f'"{name}" {identity.industry} event',
            ]
        )

    if identity.event_focus:
        queries.extend(
            [
                f'"{name}" {identity.event_focus}',
                f'"{name}" {identity.event_focus} sponsorship',
            ]
        )

    if identity.services:
        queries.append(f'"{name}" {identity.services}')

    for role in identity.target_roles:
        queries.append(f'site:linkedin.com/in "{name}" "{role}"')

    if identity.linkedin_company_url:
        match = LINKEDIN_COMPANY_RE.search(identity.linkedin_company_url)
        if match:
            slug = match.group(1)
            queries.append(f"site:linkedin.com/company/{slug}")
            queries.append(f'"{slug}" "{name}" linkedin')

    domain = _website_domain(identity.website)
    if domain:
        queries.extend(
            [
                f"site:{domain}",
                f"site:{domain} events",
                f"site:{domain} news",
                f"site:{domain} press",
                f"site:{domain} leadership",
                f"site:{domain} marketing",
                f"site:{domain} team",
                f"site:{domain} about",
            ]
        )

    deduped = []
    seen = set()
    for query in queries:
        if query not in seen:
            seen.add(query)
            deduped.append(query)
    return deduped
