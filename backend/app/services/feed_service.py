from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident

async def get_recent_incidents(db: AsyncSession, limit: int = 50):
    query = select(Incident).order_by(Incident.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def generate_json_feed(db: AsyncSession) -> list[dict]:
    incidents = await get_recent_incidents(db)
    feed = []
    for inc in incidents:
        feed.append({
            "id": str(inc.id),
            "title": inc.title,
            "description": inc.description,
            "attack_type": inc.attack_type,
            "severity": inc.severity,
            "source_url": inc.source_url,
            "published_at": inc.published_at.isoformat() if inc.published_at else None,
        })
    return feed

async def generate_rss_feed(db: AsyncSession) -> str:
    incidents = await get_recent_incidents(db)
    items = []
    for inc in incidents:
        items.append(f"""
        <item>
            <title><![CDATA[{inc.title}]]></title>
            <link>{inc.source_url}</link>
            <description><![CDATA[{inc.description or ''}]]></description>
            <guid>{inc.id}</guid>
        </item>
        """)
        
    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Indian Cyber Incident Feed</title>
    <link>http://localhost:8000</link>
    <description>Real-time cyber incident intelligence for Indian cyberspace</description>
    {''.join(items)}
</channel>
</rss>
"""
    return rss
