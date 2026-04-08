"""CLI entry point for IceBreaker."""

from __future__ import annotations

import asyncio
import logging
import sys

import click
from rich.console import Console

from .config import Config
from .output import brief_to_html, brief_to_json, brief_to_markdown, print_brief
from .pipeline import run_pipeline
from .resolver import resolve
from .synthesizer import synthesize

console = Console()


@click.command()
@click.argument("query")
@click.option("--name", "-n", default=None, help="Full name (helps disambiguate)")
@click.option("--email", "-e", default=None, help="Email address")
@click.option("--company", "-c", default=None, help="Company name (helps disambiguate)")
@click.option("--location", "-l", default=None, help="City/location (helps disambiguate)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "markdown", "json", "html"]),
    default="rich",
    help="Output format",
)
@click.option(
    "--save",
    type=click.Path(),
    default=None,
    help="Save the brief to a file (markdown format)",
)
@click.option(
    "--max-results",
    type=int,
    default=None,
    help="Max search results per query",
)
@click.option(
    "--scrape-pages",
    type=int,
    default=None,
    help="Max pages to scrape for content",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Claude model to use for synthesis",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
@click.option("--debug", is_flag=True, help="Debug logging")
def main(
    query: str,
    name: str | None,
    email: str | None,
    company: str | None,
    location: str | None,
    output_format: str,
    save: str | None,
    max_results: int | None,
    scrape_pages: int | None,
    model: str | None,
    verbose: bool,
    debug: bool,
):
    """Build a meeting prep brief from public information.

    QUERY can be an email, LinkedIn URL, Twitter URL, or person's name.
    Use --name, --company, --location to disambiguate common names.

    \b
    Examples:
      icebreaker "jane.doe@company.com"
      icebreaker "Jane Doe" --company "Acme Corp" --location "San Francisco"
      icebreaker "https://linkedin.com/in/janedoe"
      icebreaker "pram.patel@gmail.com" --name "Pramod Patel" --company "TechCo"
    """
    # Set up logging
    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    try:
        config = Config()
    except Exception as e:
        console.print(f"[red]Config error: {e}[/red]")
        console.print("Make sure you have a .env file. See .env.example")
        sys.exit(1)

    # Apply CLI overrides
    if max_results:
        config.max_search_results = max_results
    if scrape_pages:
        config.scrape_max_pages = scrape_pages
    if model:
        config.claude_model = model

    # Validate
    if not config.has_anthropic():
        console.print("[red]Error: ICEBREAKER_ANTHROPIC_API_KEY is required[/red]")
        sys.exit(1)

    if not config.has_serpapi() and not config.has_google_cse():
        console.print("[dim]No SerpAPI/Google CSE key found — using DuckDuckGo (free, no key needed)[/dim]")

    # Resolve identity with all available signals
    identity = resolve(query, name=name, email=email, company=company, location=location)

    console.print(f"[bold]Target:[/bold] {identity.full_name or identity.raw_input}")
    if identity.email:
        console.print(f"[dim]Email: {identity.email}[/dim]")
    if company:
        console.print(f"[dim]Company: {company}[/dim]")
    if location:
        console.print(f"[dim]Location: {location}[/dim]")
    console.print(f"[dim]Search queries: {identity.search_queries}[/dim]")
    console.print()

    # Run pipeline
    with console.status("[bold blue]Gathering public information..."):
        profile = asyncio.run(run_pipeline(identity, config))

    total = len(profile.all_results())
    console.print(f"[green]Found {total} data points from {len(profile.collector_results)} sources[/green]")

    if total == 0:
        console.print("[yellow]No public information found. Try adding --company or --location to narrow results.[/yellow]")
        sys.exit(0)

    # Synthesize
    with console.status("[bold blue]Analyzing with Claude..."):
        brief = asyncio.run(synthesize(profile, config))

    # Output
    if output_format == "json":
        console.print(brief_to_json(brief))
    elif output_format == "markdown":
        console.print(brief_to_markdown(brief))
    elif output_format == "html":
        import os
        import webbrowser

        html = brief_to_html(brief)
        html_path = save or f"{brief.subject_name.replace(' ', '_').lower()}_brief.html"
        with open(html_path, "w") as f:
            f.write(html)
        console.print(f"[green]HTML brief saved to {html_path}[/green]")
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        save = None  # already saved
    else:
        print_brief(brief, console)

    # Save if requested
    if save:
        if output_format == "json":
            content = brief_to_json(brief)
        else:
            content = brief_to_markdown(brief)
        with open(save, "w") as f:
            f.write(content)
        console.print(f"[green]Brief saved to {save}[/green]")


if __name__ == "__main__":
    main()
