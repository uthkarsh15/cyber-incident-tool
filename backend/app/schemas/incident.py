from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# --- Base ---
class IncidentBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    attack_type: str = Field(default="unknown", max_length=50)
    severity: str = Field(default="info", max_length=20)
    source_url: str = Field(..., max_length=2048)
    published_at: Optional[datetime] = None


# --- Create (used by agents internally) ---
class IncidentCreate(IncidentBase):
    raw_content: Optional[str] = None
    source_id: Optional[UUID] = None
    sector_id: Optional[UUID] = None
    confidence_score: float = 0.0
    india_relevance_score: float = 0.0
    metadata: dict = Field(default_factory=dict)


# --- Update ---
class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    attack_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    sector_id: Optional[UUID] = None


# --- Response (returned by API) ---
class IncidentResponse(IncidentBase):
    id: UUID
    status: str
    confidence_score: float
    india_relevance_score: float
    metadata: dict
    source_id: Optional[UUID] = None
    sector_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- List response with pagination ---
class IncidentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    incidents: list[IncidentResponse]
