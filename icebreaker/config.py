"""Configuration management via environment variables / .env file."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # Required
    anthropic_api_key: str = ""

    # Google Search - SerpAPI
    serpapi_key: str = ""

    # Google Custom Search Engine (alternative to SerpAPI)
    google_cse_key: str = ""
    google_cse_id: str = ""

    # Optional - Phase 2
    proxycurl_key: str = ""
    github_token: str = ""

    # Behavior
    cache_dir: str = "~/.icebreaker/cache"
    cache_ttl_hours: int = 24
    claude_model: str = "claude-sonnet-4-20250514"
    max_search_results: int = 20
    scrape_max_pages: int = 5
    request_timeout: float = 15.0

    model_config = {
        "env_file": ".env",
        "env_prefix": "ICEBREAKER_",
        "extra": "ignore",
    }

    def has_serpapi(self) -> bool:
        return bool(self.serpapi_key)

    def has_google_cse(self) -> bool:
        return bool(self.google_cse_key and self.google_cse_id)

    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    def has_proxycurl(self) -> bool:
        return bool(self.proxycurl_key)
