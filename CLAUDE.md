# IceBreaker - Project Guide

## What is this?
AI-powered CLI tool that builds relationship intelligence profiles from public information for meeting preparation. Given a name, email, or social URL, it scrapes public data and uses Claude AI to synthesize personality-rich meeting briefs.

## Tech Stack
- **Language:** Python 3.9+ (target 3.11+)
- **CLI:** Click
- **AI:** Anthropic Claude API (claude-sonnet-4-20250514)
- **HTTP:** httpx (async)
- **Scraping:** BeautifulSoup4 + lxml
- **Search:** DuckDuckGo (free default), SerpAPI/Google CSE (optional paid)
- **Config:** pydantic-settings with .env file
- **Output:** Rich (terminal), Markdown, JSON, HTML (interactive dashboard)
- **HTML Viz:** Chart.js (CDN) for radar charts, vanilla CSS/JS for mind map, timeline, cards

## Project Structure
```
icebreaker/
├── cli.py              # Click CLI entry point
├── config.py           # Config class (pydantic-settings, env prefix: ICEBREAKER_)
├── models.py           # Data classes: ResolvedIdentity, SearchResult, CollectorResult, ProfileData, MeetingBrief
├── resolver.py         # Input parsing: resolve() detects email/LinkedIn/Twitter/name
├── pipeline.py         # Orchestrator: run_pipeline() runs collectors then scrapes URLs
├── synthesizer.py      # Claude integration: synthesize() sends data to Claude, returns MeetingBrief
├── output.py           # Formatting: print_brief(), brief_to_markdown(), brief_to_json(), brief_to_html()
├── templates/
│   ├── __init__.py     # Package marker
│   └── profile.html    # Self-contained HTML template (Chart.js radar, mind map, timeline, cards)
└── collectors/
    ├── __init__.py     # get_available_collectors(config) registry
    ├── base.py         # AbstractCollector base class
    ├── duckduckgo.py   # Free search (always available)
    ├── google_search.py # Paid search (SerpAPI or Google CSE)
    └── web_scraper.py  # URL content extraction
```

## How to Run
```bash
# Activate venv
source .venv/bin/activate

# Basic usage
icebreaker "Jane Doe" --company "Acme Corp"
icebreaker "jane@example.com"
icebreaker "https://linkedin.com/in/janedoe"

# Options
--format rich|markdown|json|html
--save output.md
--verbose / --debug
--max-results N
--scrape-pages N
--model <claude-model-id>
```

## Environment Variables
- `ICEBREAKER_ANTHROPIC_API_KEY` (required) - Claude API key
- `ICEBREAKER_SERPAPI_KEY` (optional) - SerpAPI for Google search
- `ICEBREAKER_GOOGLE_CSE_KEY` / `ICEBREAKER_GOOGLE_CSE_ID` (optional)
- `ICEBREAKER_PROXYCURL_KEY` (optional, phase 2)
- `ICEBREAKER_GITHUB_TOKEN` (optional)

## Data Flow
1. **Resolve** input → `ResolvedIdentity` with search queries
2. **Collect** data via DuckDuckGo/Google → `ProfileData`
3. **Scrape** discovered URLs for full content
4. **Synthesize** with Claude → `MeetingBrief`
5. **Output** to terminal/file

## Key Patterns
- Config class is `Config` (not `Settings`) in `config.py`
- Resolver is a module-level `resolve()` function (not a class)
- Collectors follow plugin pattern with `AbstractCollector` base
- Pipeline and synthesizer use `async/await`
- CLI wraps async with `asyncio.run()`

## Current State
- Feature-complete MVP with working end-to-end pipeline
- HTML visual output with interactive mind map, radar chart, timeline, collapsible sections, dark/light theme
- HTML format auto-opens in browser when used with `--format html`
- Tests directory exists but is empty (no tests yet)
- Caching system planned but not implemented
- Web UI (Streamlit) and PDF export planned for phase 2

## Development Notes
- Python version in venv is 3.9.6; pyproject.toml says >=3.11 (works on 3.9 with `from __future__ import annotations`)
- DuckDuckGo search library is sync-only, wrapped in thread pool executor
- HTML template uses `{{BRIEF_DATA}}` and `{{SUBJECT_NAME}}` placeholders replaced via str.replace (not string.Template, to avoid CSS $ conflicts)
- HTML format auto-saves file and opens in browser (no console print of raw HTML)
- Always update CLAUDE.md and memory when making significant changes
