import json
import asyncio
import logging
import redis.asyncio as redis
from app.config import settings
from app.agents.relevance_agent import RelevanceAgent
from app.agents.classification_agent import ClassificationAgent
from app.agents.correlation_agent import CorrelationAgent
from app.agents.insight_agent import InsightAgent

class PipelineOrchestrator:
    def __init__(self):
        self.relevance_agent = RelevanceAgent()
        self.classification_agent = ClassificationAgent()
        self.correlation_agent = CorrelationAgent()
        self.insight_agent = InsightAgent()
        self.pipeline = [
            self.relevance_agent,
            self.classification_agent,
            self.correlation_agent,
            self.insight_agent,
        ]
        self.redis = redis.from_url(settings.redis_url)
        self.logger = logging.getLogger("orchestrator")
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def process_article(self, raw_article: dict) -> dict | None:
        data = raw_article
        for agent in self.pipeline:
            data = await agent.process(data)
            if data is None:
                return None
        return data

    async def consume_queue(self):
        self.logger.info("Starting orchestrator queue consumer...")
        while True:
            try:
                raw = await self.redis.blpop("incident:raw", timeout=30)
                if raw:
                    article = json.loads(raw[1])
                    await self.process_article(article)
            except Exception as e:
                self.logger.error(f"Error consuming queue: {e}")
                await asyncio.sleep(5)
