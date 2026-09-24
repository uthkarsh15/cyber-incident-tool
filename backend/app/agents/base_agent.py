import logging
from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    """Base class for all processing agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    @abstractmethod
    async def process(self, data: dict) -> dict | None:
        """Process a single data item."""
        pass

    async def run_batch(self, items: list[dict]) -> list[dict]:
        """Process a batch of items."""
        results = []
        for item in items:
            try:
                result = await self.process(item)
                if result is not None:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing item: {e}", exc_info=True)
        return results
