from uuid import UUID
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate

async def create_incident(db: AsyncSession, data: IncidentCreate) -> Incident:
    incident = Incident(**data.model_dump())
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident

async def get_incident(db: AsyncSession, id: UUID) -> Incident | None:
    result = await db.execute(select(Incident).where(Incident.id == id))
    return result.scalar_one_or_none()

async def list_incidents(db: AsyncSession, page: int, page_size: int, filters: dict) -> tuple[list[Incident], int]:
    query = select(Incident)
    
    if filters.get("attack_type"):
        query = query.where(Incident.attack_type == filters["attack_type"])
    if filters.get("severity"):
        query = query.where(Incident.severity == filters["severity"])
    if filters.get("sector_id"):
        query = query.where(Incident.sector_id == filters["sector_id"])
        
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    
    # Pagination
    query = query.order_by(Incident.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    incidents = (await db.execute(query)).scalars().all()
    
    return list(incidents), total

async def update_incident(db: AsyncSession, id: UUID, data: IncidentUpdate) -> Incident | None:
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return await get_incident(db, id)
        
    await db.execute(update(Incident).where(Incident.id == id).values(**update_data))
    await db.commit()
    return await get_incident(db, id)

async def delete_incident(db: AsyncSession, id: UUID) -> bool:
    result = await db.execute(delete(Incident).where(Incident.id == id))
    await db.commit()
    return result.rowcount > 0
