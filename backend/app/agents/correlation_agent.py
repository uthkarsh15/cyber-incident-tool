from app.agents.base_agent import BaseAgent
from sqlalchemy import select
from app.database import async_session
from app.models.incident import Incident
from datetime import datetime, timezone, timedelta

class CorrelationAgent(BaseAgent):
    def __init__(self):
        super().__init__("correlation")

    async def _find_by_url(self, url: str) -> bool:
        async with async_session() as session:
            result = await session.execute(select(Incident.id).where(Incident.source_url == url))
            return result.scalar_one_or_none() is not None

    async def _get_recent_incidents(self, days: int):
        async with async_session() as session:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            result = await session.execute(select(Incident).where(Incident.created_at >= cutoff))
            return result.scalars().all()

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def _find_shared_entities(self, data: dict, incident: Incident) -> dict | None:
        import re
        cves_a = set(re.findall(r"CVE-\d{4}-\d{4,}", data.get("title", "")))
        cves_b = set(re.findall(r"CVE-\d{4}-\d{4,}", incident.title))
        if cves_a & cves_b:
            return {"type": "same_cve"}
        return None

    async def process(self, data: dict) -> dict | None:
        try:
            if await self._find_by_url(data["source_url"]):
                self.logger.info(f"Duplicate skipped: {data['source_url']}")
                return None
            recent_incidents = await self._get_recent_incidents(days=7)
        except Exception as e:
            self.logger.warning(f"Database unavailable for correlation, skipping similarity checks: {e}")
            recent_incidents = []
        correlations = []

        for incident in recent_incidents:
            sim = self._jaccard_similarity(data["title"], incident.title)
            if sim > 0.6:
                correlations.append({
                    "incident_id": str(incident.id),
                    "similarity_score": sim,
                    "correlation_type": "same_event",
                })
                continue

            shared_entities = self._find_shared_entities(data, incident)
            if shared_entities:
                correlations.append({
                    "incident_id": str(incident.id),
                    "similarity_score": 0.7,
                    "correlation_type": shared_entities["type"],
                })

        data["correlations"] = correlations
        return data
