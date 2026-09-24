import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.entity import Sector
from app.models.source import Source


SEED_SECTORS = [
    {"name": "Government", "code": "government"},
    {"name": "Banking & Finance", "code": "banking_finance"},
    {"name": "Healthcare", "code": "healthcare"},
    {"name": "Energy & Power", "code": "energy_power"},
    {"name": "Telecom", "code": "telecom"},
    {"name": "Defence", "code": "defence"},
    {"name": "Transportation", "code": "transportation"},
    {"name": "Education", "code": "education"},
    {"name": "IT & ITES", "code": "it_ites"},
    {"name": "Manufacturing", "code": "manufacturing"},
    {"name": "Media", "code": "media"},
    {"name": "Retail & E-commerce", "code": "retail_ecommerce"},
    {"name": "Other", "code": "other"},
]

SEED_SOURCES = [
    {
        "name": "CERT-In",
        "url": "https://www.cert-in.org.in/",
        "source_type": "government_advisory",
    },
    {
        "name": "The Hacker News",
        "url": "https://thehackernews.com/",
        "source_type": "news_article",
    },
    {
        "name": "BleepingComputer",
        "url": "https://www.bleepingcomputer.com/",
        "source_type": "news_article",
    },
]

async def seed_db():
    async with async_session() as session:
        # Seed Sectors
        for s in SEED_SECTORS:
            result = await session.execute(select(Sector).where(Sector.code == s["code"]))
            if not result.scalar_one_or_none():
                session.add(Sector(**s))
        
        # Seed Sources
        for s in SEED_SOURCES:
            result = await session.execute(select(Source).where(Source.name == s["name"]))
            if not result.scalar_one_or_none():
                session.add(Source(**s))
                
        await session.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_db())
