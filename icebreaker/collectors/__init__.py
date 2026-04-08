"""Collector registry - auto-discovers and registers all collectors."""

from .base import AbstractCollector

_REGISTRY: dict[str, type[AbstractCollector]] = {}


def register(cls: type[AbstractCollector]) -> type[AbstractCollector]:
    """Decorator to register a collector class."""
    _REGISTRY[cls.name] = cls
    return cls


def get_all_collectors() -> dict[str, type[AbstractCollector]]:
    return dict(_REGISTRY)


def get_available_collectors(config) -> list[type[AbstractCollector]]:
    """Return only collectors whose dependencies (API keys etc.) are met."""
    return [cls for cls in _REGISTRY.values() if cls.check_available(config)]


# Import collectors to trigger registration
from . import duckduckgo  # noqa: E402, F401
from . import google_search  # noqa: E402, F401
from . import web_scraper  # noqa: E402, F401
