import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    attack_type = Column(String(50), nullable=False, default="unknown")
    severity = Column(String(20), nullable=False, default="info")
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    source_url = Column(String(2048), nullable=False, unique=True)
    sector_id = Column(UUID(as_uuid=True), ForeignKey("sectors.id"), nullable=True)
    status = Column(String(20), default="new")
    confidence_score = Column(Float, default=0.0)
    india_relevance_score = Column(Float, default=0.0)
    metadata_ = Column("metadata", JSONB, default={})
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    source = relationship("Source", back_populates="incidents")
    sector = relationship("Sector", back_populates="incidents")
    incident_entities = relationship("IncidentEntity", back_populates="incident")

    __table_args__ = (
        Index("idx_incidents_attack_type", "attack_type"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_created_at", "created_at"),
    )
