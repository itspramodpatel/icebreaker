"""Claude-powered synthesis - turns raw data into a meeting prep brief."""

from __future__ import annotations

import json
import logging

import anthropic

from .config import Config
from .models import MeetingBrief, ProfileData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a relationship intelligence analyst. Your job is to build a deep, nuanced \
profile of a person from publicly available data — going far beyond just their job title.

Your goal: Help someone walking into a first meeting truly UNDERSTAND this person — \
their personality, what they care about, what makes them tick, what they post about, \
what causes they support, how they communicate, and what would genuinely connect with them.

ANALYSIS APPROACH:
1. SOCIAL PRESENCE: Map every platform they're active on. Note follower counts, \
   posting frequency, engagement levels. Are they a lurker or a thought leader?
2. CONTENT ANALYSIS: What do they share, like, comment on? What topics recur? \
   What's the tone — formal, casual, humorous, technical, inspirational?
3. PERSONAL INTERESTS: Go beyond "technology" — find specific hobbies, sports teams, \
   travel destinations, food preferences, books, music, movies they've mentioned.
4. VALUES & CAUSES: Do they post about sustainability, education, diversity, startups, \
   open source, mental health, family? What do they champion?
5. PERSONALITY SIGNALS: Introvert/extrovert signals, humor style, formality level, \
   how they interact with others online. Are they a mentor type? A builder? A connector?
6. COMMUNICATION STYLE: Do they write long thoughtful posts or quick hot takes? \
   Do they use emojis? Are they data-driven or storytelling-oriented?

Rules:
- Only include information clearly about the target person (filter out same-name people)
- Be factual — never speculate about private matters, health, or relationships
- When data is thin, be honest about gaps rather than padding with generic filler
- Flag ambiguity in warnings
- Cite specific posts/content when possible

Output a JSON object with this structure:
{
    "subject_name": "Full Name",
    "professional_summary": "2-3 sentence professional background",
    "social_presence": {
        "platforms": ["platform1: description of activity level", ...],
        "overall_visibility": "low/medium/high — how much of a public footprint they have",
        "audience_size": "approximate total following across platforms",
        "posting_style": "description of how they engage online"
    },
    "personal_interests": ["specific interest with detail", ...],
    "personality_traits": ["trait with evidence", ...],
    "values_and_causes": ["cause/value they champion with evidence", ...],
    "content_they_share": ["type of content with examples", ...],
    "communication_style": "paragraph describing how they communicate",
    "conversation_starters": ["highly specific starter referencing actual content", ...],
    "recent_activity": ["recent thing with date if available", ...],
    "key_topics": ["topic they genuinely care about", ...],
    "warnings": ["any caveats about data quality", ...],
    "sources_used": ["source1.com", "source2.com", ...]
}

Make every field SPECIFIC, not generic. "Interested in technology" is useless. \
"Passionate about 3D animation pipelines and has been sharing content about real-time \
rendering workflows" is valuable. Reference actual posts, videos, articles when possible."""

USER_PROMPT_TEMPLATE = """\
Build a deep personal profile and Meeting Prep Brief for this person.

**Input provided:** {raw_input}
**Detected name:** {name}
**Detected email:** {email}

**Raw data from public sources:**

{raw_data}

Analyze ALL the above data deeply. Look for patterns in what they share, like, and \
engage with. Build a rich profile that goes beyond their resume — capture who they ARE, \
not just what they do. Focus on personal interests, social behavior, values, and \
specific conversation starters that would genuinely connect."""


def _format_raw_data(profile: ProfileData) -> str:
    """Format all collected data into a readable string for Claude."""
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
                # Give more content to Claude for deeper analysis
                content = sr.content[:3000]
                lines.append(f"Content: {content}")
            if sr.date:
                lines.append(f"Date: {sr.date}")
            if lines:
                section_lines.append("\n".join(lines))
                section_lines.append("---")

        sections.append("\n".join(section_lines))

    return "\n\n".join(sections) if sections else "(No data collected)"


async def synthesize(profile: ProfileData, config: Config) -> MeetingBrief:
    """Use Claude to synthesize collected data into a meeting brief."""
    if not config.has_anthropic():
        raise ValueError(
            "Anthropic API key required. Set ICEBREAKER_ANTHROPIC_API_KEY in .env"
        )

    raw_data = _format_raw_data(profile)
    identity = profile.identity

    user_prompt = USER_PROMPT_TEMPLATE.format(
        raw_input=identity.raw_input,
        name=identity.full_name or "(not detected)",
        email=identity.email or "(not provided)",
        raw_data=raw_data,
    )

    logger.info(f"Sending {len(raw_data)} chars to Claude for synthesis")

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model=config.claude_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract JSON from response
    response_text = message.content[0].text
    logger.debug(f"Claude response: {response_text[:500]}")

    # Try to parse JSON - handle cases where Claude wraps in markdown code blocks
    json_str = response_text
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        data = json.loads(json_str.strip())
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Claude response as JSON: {response_text[:200]}")
        return MeetingBrief(
            subject_name=identity.full_name or identity.raw_input,
            professional_summary=response_text[:500],
            personal_interests=[],
            conversation_starters=[],
            recent_activity=[],
            key_topics=[],
            warnings=["Failed to parse structured response - showing raw analysis"],
            sources_used=[],
            raw_json={},
        )

    social = data.get("social_presence", {})
    if isinstance(social, list):
        social = {"platforms": social}

    return MeetingBrief(
        subject_name=data.get("subject_name", identity.full_name or identity.raw_input),
        professional_summary=data.get("professional_summary", ""),
        personal_interests=data.get("personal_interests", []),
        conversation_starters=data.get("conversation_starters", []),
        recent_activity=data.get("recent_activity", []),
        key_topics=data.get("key_topics", []),
        warnings=data.get("warnings", []),
        sources_used=data.get("sources_used", []),
        social_presence=social,
        personality_traits=data.get("personality_traits", []),
        values_and_causes=data.get("values_and_causes", []),
        content_they_share=data.get("content_they_share", []),
        communication_style=data.get("communication_style", ""),
        raw_json=data,
    )
