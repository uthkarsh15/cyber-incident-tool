from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.incident import Incident
from app.models.entity import Sector

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Incident))).scalar_one()
    
    sev_query = select(Incident.severity, func.count()).group_by(Incident.severity)
    by_severity = {row[0]: row[1] for row in await db.execute(sev_query)}
    
    type_query = select(Incident.attack_type, func.count()).group_by(Incident.attack_type)
    by_type = {row[0]: row[1] for row in await db.execute(type_query)}
    
    sector_query = select(Sector.name, func.count(Incident.id)).outerjoin(Incident).group_by(Sector.name)
    by_sector = {row[0]: row[1] for row in await db.execute(sector_query)}
    
    return {
        "total": total,
        "by_severity": by_severity,
        "by_type": by_type,
        "by_sector": by_sector
    }

@router.get("/trends")
async def get_trends(db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM incidents
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """)
    result = await db.execute(query)
    daily_counts = [{"date": row[0].isoformat(), "count": row[1]} for row in result]
    return {"daily_counts": daily_counts}
