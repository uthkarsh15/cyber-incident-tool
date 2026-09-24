from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse, IncidentListResponse
from app.services import incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    attack_type: Optional[str] = None,
    severity: Optional[str] = None,
    sector_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    filters = {
        "attack_type": attack_type,
        "severity": severity,
        "sector_id": sector_id
    }
    incidents, total = await incident_service.list_incidents(db, page, page_size, filters)
    return IncidentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        incidents=incidents
    )

@router.get("/{id}", response_model=IncidentResponse)
async def get_incident(id: UUID, db: AsyncSession = Depends(get_db)):
    incident = await incident_service.get_incident(db, id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(data: IncidentCreate, db: AsyncSession = Depends(get_db)):
    return await incident_service.create_incident(db, data)

@router.patch("/{id}", response_model=IncidentResponse)
async def update_incident(id: UUID, data: IncidentUpdate, db: AsyncSession = Depends(get_db)):
    incident = await incident_service.update_incident(db, id, data)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.delete("/{id}", status_code=204)
async def delete_incident(id: UUID, db: AsyncSession = Depends(get_db)):
    success = await incident_service.delete_incident(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
