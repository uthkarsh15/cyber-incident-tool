from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SourceBase(BaseModel):
    name: str = Field(..., max_length=255)
    url: str = Field(..., max_length=2048)
    source_type: str = Field(..., max_length=50)


class SourceCreate(SourceBase):
    is_active: bool = True
    scrape_config: Optional[dict] = None


class SourceResponse(SourceBase):
    id: UUID
    is_active: bool
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
