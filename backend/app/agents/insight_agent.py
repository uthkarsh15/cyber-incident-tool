try:
    import spacy
except ImportError:
    spacy = None

import re
from datetime import datetime
from app.agents.base_agent import BaseAgent
from app.database import async_session
from app.models.incident import Incident
from app.models.entity import Entity, IncidentEntity, Sector
from app.models.source import Source
from app.schemas.incident import IncidentCreate
from sqlalchemy import select

class InsightAgent(BaseAgent):
    def __init__(self):
        super().__init__("insight")
        self.nlp = None
        if spacy is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                self.logger.warning("Spacy model 'en_core_web_sm' not found. Will skip NLP NER extraction.")
        else:
            self.logger.warning("Spacy not installed. Will use regex-based entity extraction.")

    def _map_spacy_label(self, label: str) -> str:
        mapping = {
            "ORG": "organization",
            "GPE": "country",
            "PERSON": "threat_actor",
            "PRODUCT": "software",
        }
        return mapping.get(label, "other")

    def _generate_summary(self, data: dict) -> str:
        content = data.get("content", "")
        return content[:500].strip() + "..." if len(content) > 500 else content

    @staticmethod
    def _parse_published_at(raw) -> datetime | None:
        if not raw:
            return None
        if isinstance(raw, datetime):
            return raw
        s = str(raw).strip()
        if not s:
            return None
        formats = [
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S%z",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    async def _save_to_database(self, data: dict) -> None:
        async with async_session() as session:
            sector_id = None
            if data.get("sector_code"):
                result = await session.execute(select(Sector.id).where(Sector.code == data["sector_code"]))
                sector_id = result.scalar_one_or_none()

            source_id = None
            if data.get("source_name"):
                result = await session.execute(select(Source.id).where(Source.name == data["source_name"]))
                source_id = result.scalar_one_or_none()

            published_at = self._parse_published_at(data.get("published_at"))

            incident_data = IncidentCreate(
                title=data.get("title", "Unknown"),
                description=data.get("description"),
                attack_type=data.get("attack_type", "unknown"),
                severity=data.get("severity", "info"),
                source_url=data.get("source_url"),
                published_at=published_at,
                raw_content=data.get("content"),
                source_id=source_id,
                sector_id=sector_id,
                confidence_score=data.get("confidence_score", 0.0),
                india_relevance_score=data.get("india_relevance_score", 0.0),
                metadata=data.get("extra", {}),
            )

            payload = incident_data.model_dump()
            payload["metadata_"] = payload.pop("metadata", {})
            incident = Incident(**payload)
            session.add(incident)
            await session.commit()
            await session.refresh(incident)
            
            for ent_data in data.get("extracted_entities", []):
                ent_name = ent_data["name"]
                ent_type = ent_data["entity_type"]
                result = await session.execute(
                    select(Entity).where(Entity.name == ent_name).where(Entity.entity_type == ent_type)
                )
                entity = result.scalar_one_or_none()
                if not entity:
                    entity = Entity(name=ent_name, entity_type=ent_type)
                    session.add(entity)
                    await session.commit()
                    await session.refresh(entity)
                
                ie = IncidentEntity(incident_id=incident.id, entity_id=entity.id, role="mentioned")
                session.add(ie)
            
            await session.commit()
            data["incident_id"] = str(incident.id)

    async def process(self, data: dict) -> dict | None:
        text = data.get("content", "")
        entities = []

        if self.nlp:
            doc = self.nlp(text[:10000])
            for ent in doc.ents:
                if ent.label_ in ("ORG", "GPE", "PERSON", "PRODUCT"):
                    entities.append({
                        "name": ent.text,
                        "entity_type": self._map_spacy_label(ent.label_),
                    })

        cves = re.findall(r"CVE-\d{4}-\d{4,}", text)
        for cve in cves:
            entities.append({"name": cve, "entity_type": "cve_id"})

        ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)
        for ip in ips:
            entities.append({"name": ip, "entity_type": "ip_address"})

        unique_entities = { (e["name"], e["entity_type"]): e for e in entities }.values()
        data["extracted_entities"] = list(unique_entities)

        data["description"] = self._generate_summary(data)

        try:
            await self._save_to_database(data)
        except Exception as e:
            self.logger.error(f"Failed to save incident: {e}")
            return None

        return data
