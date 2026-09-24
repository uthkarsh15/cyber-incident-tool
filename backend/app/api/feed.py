from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["feed"])

@router.get("/json")
async def get_json_feed(db: AsyncSession = Depends(get_db)):
    return await feed_service.generate_json_feed(db)

@router.get("/rss")
async def get_rss_feed(db: AsyncSession = Depends(get_db)):
    rss_content = await feed_service.generate_rss_feed(db)
    return Response(content=rss_content, media_type="application/rss+xml")
