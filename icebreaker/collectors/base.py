"""Abstract base class for all collectors."""

from abc import ABC, abstractmethod

import httpx

from ..config import Config
from ..models import CollectorResult, ResolvedIdentity


class AbstractCollector(ABC):
    name: str = "base"

    def __init__(self, config: Config, client: httpx.AsyncClient):
        self.config = config
        self.client = client

    @abstractmethod
    async def collect(self, identity: ResolvedIdentity) -> CollectorResult:
        """Gather data for the resolved identity. Must not raise."""
        ...

    @classmethod
    @abstractmethod
    def check_available(cls, config: Config) -> bool:
        """Check if required API keys / dependencies are present."""
        ...
