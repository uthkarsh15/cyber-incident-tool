import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    incident_entities = relationship("IncidentEntity", back_populates="entity")

    __table_args__ = (
        UniqueConstraint("name", "entity_type", name="uq_entity_name_type"),
    )


class IncidentEntity(Base):
    __tablename__ = "incident_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False)
    role = Column(String(50), default="mentioned")

    incident = relationship("Incident", back_populates="incident_entities")
    entity = relationship("Entity", back_populates="incident_entities")


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(String(500), nullable=True)

    incidents = relationship("Incident", back_populates="sector")


class Correlation(Base):
    __tablename__ = "correlations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_a_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    incident_b_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    correlation_type = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
