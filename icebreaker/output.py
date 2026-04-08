"""Output formatting - Rich console, JSON, Markdown, HTML."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .models import MeetingBrief


def print_brief(brief: MeetingBrief, console: Console | None = None) -> None:
    """Print a meeting brief with Rich formatting."""
    c = console or Console()

    # Header
    c.print()
    c.print(
        Panel(
            f"[bold]{brief.subject_name}[/bold]",
            title="Meeting Prep Brief",
            subtitle="Generated from public information",
            style="blue",
        )
    )

    # Professional Summary
    if brief.professional_summary:
        c.print()
        c.print("[bold cyan]Professional Summary[/bold cyan]")
        c.print(brief.professional_summary)

    # Social Presence
    if brief.social_presence:
        c.print()
        c.print("[bold magenta]Social Presence[/bold magenta]")
        sp = brief.social_presence
        if sp.get("overall_visibility"):
            c.print(f"  Visibility: [bold]{sp['overall_visibility']}[/bold]")
        if sp.get("audience_size"):
            c.print(f"  Audience: {sp['audience_size']}")
        if sp.get("posting_style"):
            c.print(f"  Style: {sp['posting_style']}")
        if sp.get("platforms"):
            c.print("  Platforms:")
            for platform in sp["platforms"]:
                c.print(f"    - {platform}")

    # Personality Traits
    if brief.personality_traits:
        c.print()
        c.print("[bold magenta]Personality Signals[/bold magenta]")
        for trait in brief.personality_traits:
            c.print(f"  - {trait}")

    # Communication Style
    if brief.communication_style:
        c.print()
        c.print("[bold magenta]Communication Style[/bold magenta]")
        c.print(f"  {brief.communication_style}")

    # Personal Interests
    if brief.personal_interests:
        c.print()
        c.print("[bold cyan]Personal Interests & Hobbies[/bold cyan]")
        for interest in brief.personal_interests:
            c.print(f"  - {interest}")

    # Values & Causes
    if brief.values_and_causes:
        c.print()
        c.print("[bold cyan]Values & Causes[/bold cyan]")
        for cause in brief.values_and_causes:
            c.print(f"  - {cause}")

    # Content They Share
    if brief.content_they_share:
        c.print()
        c.print("[bold cyan]Content They Share[/bold cyan]")
        for content in brief.content_they_share:
            c.print(f"  - {content}")

    # Conversation Starters
    if brief.conversation_starters:
        c.print()
        c.print("[bold green]Conversation Starters[/bold green]")
        for i, starter in enumerate(brief.conversation_starters, 1):
            c.print(f"  {i}. {starter}")

    # Recent Activity
    if brief.recent_activity:
        c.print()
        c.print("[bold cyan]Recent Activity[/bold cyan]")
        for activity in brief.recent_activity:
            c.print(f"  - {activity}")

    # Key Topics
    if brief.key_topics:
        c.print()
        c.print("[bold cyan]Key Topics They Care About[/bold cyan]")
        for topic in brief.key_topics:
            c.print(f"  - {topic}")

    # Warnings
    if brief.warnings:
        c.print()
        c.print("[bold yellow]Notes & Caveats[/bold yellow]")
        for warning in brief.warnings:
            c.print(f"  - {warning}")

    # Sources
    if brief.sources_used:
        c.print()
        c.print("[dim]Sources: " + ", ".join(brief.sources_used) + "[/dim]")

    c.print()
    c.print(
        "[dim italic]This brief was generated from publicly available information.[/dim italic]"
    )
    c.print()


def brief_to_json(brief: MeetingBrief) -> str:
    """Convert brief to JSON string."""
    return json.dumps(brief.raw_json, indent=2)


def brief_to_markdown(brief: MeetingBrief) -> str:
    """Convert brief to Markdown string."""
    lines = [
        f"# Meeting Prep Brief: {brief.subject_name}",
        "",
    ]

    if brief.professional_summary:
        lines.extend(["## Professional Summary", brief.professional_summary, ""])

    if brief.social_presence:
        lines.append("## Social Presence")
        sp = brief.social_presence
        if sp.get("overall_visibility"):
            lines.append(f"**Visibility:** {sp['overall_visibility']}")
        if sp.get("audience_size"):
            lines.append(f"**Audience:** {sp['audience_size']}")
        if sp.get("posting_style"):
            lines.append(f"**Style:** {sp['posting_style']}")
        if sp.get("platforms"):
            for platform in sp["platforms"]:
                lines.append(f"- {platform}")
        lines.append("")

    if brief.personality_traits:
        lines.append("## Personality Signals")
        for trait in brief.personality_traits:
            lines.append(f"- {trait}")
        lines.append("")

    if brief.communication_style:
        lines.extend(["## Communication Style", brief.communication_style, ""])

    if brief.personal_interests:
        lines.append("## Personal Interests")
        for interest in brief.personal_interests:
            lines.append(f"- {interest}")
        lines.append("")

    if brief.values_and_causes:
        lines.append("## Values & Causes")
        for cause in brief.values_and_causes:
            lines.append(f"- {cause}")
        lines.append("")

    if brief.content_they_share:
        lines.append("## Content They Share")
        for content in brief.content_they_share:
            lines.append(f"- {content}")
        lines.append("")

    if brief.conversation_starters:
        lines.append("## Conversation Starters")
        for i, starter in enumerate(brief.conversation_starters, 1):
            lines.append(f"{i}. {starter}")
        lines.append("")

    if brief.recent_activity:
        lines.append("## Recent Activity")
        for activity in brief.recent_activity:
            lines.append(f"- {activity}")
        lines.append("")

    if brief.key_topics:
        lines.append("## Key Topics")
        for topic in brief.key_topics:
            lines.append(f"- {topic}")
        lines.append("")

    if brief.warnings:
        lines.append("## Notes")
        for warning in brief.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if brief.sources_used:
        lines.append(f"*Sources: {', '.join(brief.sources_used)}*")
        lines.append("")

    lines.append("---")
    lines.append("*Generated from publicly available information by IceBreaker.*")

    return "\n".join(lines)


def brief_to_html(brief: MeetingBrief) -> str:
    """Convert brief to a self-contained HTML file."""
    template_path = Path(__file__).parent / "templates" / "profile.html"
    template_text = template_path.read_text(encoding="utf-8")

    data = {
        "subject_name": brief.subject_name,
        "professional_summary": brief.professional_summary,
        "social_presence": brief.social_presence,
        "personality_traits": brief.personality_traits,
        "communication_style": brief.communication_style,
        "personal_interests": brief.personal_interests,
        "values_and_causes": brief.values_and_causes,
        "content_they_share": brief.content_they_share,
        "conversation_starters": brief.conversation_starters,
        "recent_activity": brief.recent_activity,
        "key_topics": brief.key_topics,
        "warnings": brief.warnings,
        "sources_used": brief.sources_used,
        "generated_at": brief.generated_at.isoformat(),
    }

    json_data = json.dumps(data, indent=2)

    html = template_text.replace("{{BRIEF_DATA}}", json_data)
    html = html.replace("{{SUBJECT_NAME}}", brief.subject_name)

    return html
