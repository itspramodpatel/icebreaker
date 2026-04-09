"""Claude-powered synthesis for company opportunity briefs."""

from __future__ import annotations

import json
import logging

import anthropic

from .config import Config
from .models import CompanyBrief, ProfileData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a B2B growth and research strategist. Your job is to turn public information \
about a company into an actionable opportunity brief for outbound sales and founder-led \
business development.

Your goal:
- understand the company
- infer likely current priorities from public evidence
- identify event, exhibition, activation, partnership, and campaign signals
- map likely buyer roles
- generate practical outreach angles and first-touch messaging

Rules:
- use only evidence grounded in the provided public data
- separate confirmed facts from likely inferences
- if event dates or calendars are uncertain, say so explicitly
- do not invent direct contact details
- target roles may be inferred even when named individuals are not found
- prefer concise, commercially useful output over generic company summaries

Output JSON with this structure:
{
  "company_name": "Company Name",
  "website": "https://example.com",
  "summary": "2-3 sentence commercial summary",
  "current_priorities": ["priority with evidence", "..."],
  "opportunity_signals": ["signal with why it matters", "..."],
  "events_calendar": ["event or exhibition item with date confidence note", "..."],
  "target_roles": ["role and why it matters", "..."],
  "outreach_angles": ["specific angle tied to evidence", "..."],
  "email_draft": "short personalized first-touch email",
  "linkedin_message": "short LinkedIn outreach note",
  "call_talking_points": ["talk track bullet", "..."],
  "warnings": ["data caveat", "..."],
  "sources_used": ["domain1.com", "domain2.com"]
}

Make the result useful for sales outreach planning, not just company research."""

USER_PROMPT_TEMPLATE = """\
Build a company opportunity brief for outbound planning.

Company: {company_name}
Website: {website}
Geography: {geography}
Industry: {industry}
Target roles: {target_roles}
Event focus: {event_focus}
Services offered: {services}

Raw public data:

{raw_data}

Analyze the evidence and produce a commercially useful research brief that helps \
prioritize outreach, shape messaging, and prepare sales follow-up."""


def _format_raw_data(profile: ProfileData) -> str:
    sections = []
    for cr in profile.collector_results:
        if not cr.success or not cr.results:
            continue
        section_lines = [f"### Source: {cr.source}"]
        for sr in cr.results:
            lines = []
            if sr.title:
                lines.append(f"**{sr.title}**")
            if sr.url:
                lines.append(f"URL: {sr.url}")
            if sr.snippet:
                lines.append(f"Snippet: {sr.snippet}")
            if sr.content:
                lines.append(f"Content: {sr.content[:3000]}")
            if sr.date:
                lines.append(f"Date: {sr.date}")
            if lines:
                section_lines.append("\n".join(lines))
                section_lines.append("---")
        sections.append("\n".join(section_lines))
    return "\n\n".join(sections) if sections else "(No data collected)"


async def synthesize_company(profile: ProfileData, config: Config) -> CompanyBrief:
    if not config.has_anthropic():
        raise ValueError(
            "Anthropic API key required. Set ICEBREAKER_ANTHROPIC_API_KEY in .env"
        )

    raw_data = _format_raw_data(profile)
    identity = profile.identity

    user_prompt = USER_PROMPT_TEMPLATE.format(
        company_name=getattr(identity, "company_name", identity.raw_input),
        website=getattr(identity, "website", "") or "(not provided)",
        geography=getattr(identity, "geography", "") or "(not provided)",
        industry=getattr(identity, "industry", "") or "(not provided)",
        target_roles=", ".join(getattr(identity, "target_roles", []) or []) or "(not provided)",
        event_focus=getattr(identity, "event_focus", "") or "(not provided)",
        services=getattr(identity, "services", "") or "(not provided)",
        raw_data=raw_data,
    )

    logger.info("Sending %s chars to Claude for company synthesis", len(raw_data))

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model=config.claude_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text
    json_str = response_text
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        data = json.loads(json_str.strip())
    except json.JSONDecodeError:
        logger.error("Failed to parse company response as JSON: %s", response_text[:200])
        return CompanyBrief(
            company_name=getattr(identity, "company_name", identity.raw_input),
            website=getattr(identity, "website", "") or "",
            summary=response_text[:800],
            warnings=["Failed to parse structured response - showing raw analysis"],
            raw_json={},
        )

    return CompanyBrief(
        company_name=data.get("company_name", getattr(identity, "company_name", identity.raw_input)),
        website=data.get("website", getattr(identity, "website", "") or ""),
        summary=data.get("summary", ""),
        current_priorities=data.get("current_priorities", []),
        opportunity_signals=data.get("opportunity_signals", []),
        events_calendar=data.get("events_calendar", []),
        target_roles=data.get("target_roles", []),
        outreach_angles=data.get("outreach_angles", []),
        email_draft=data.get("email_draft", ""),
        linkedin_message=data.get("linkedin_message", ""),
        call_talking_points=data.get("call_talking_points", []),
        warnings=data.get("warnings", []),
        sources_used=data.get("sources_used", []),
        raw_json=data,
    )
