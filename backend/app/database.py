import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger(__name__)


def get_sql_echo() -> bool:
    return os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")


engine = create_async_engine(settings.database_url, echo=get_sql_echo())
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    try:
        async with engine.begin() as conn:
            # Migrations will be handled by Alembic
            pass
    except Exception as e:
        logger.warning(f"Database connection failed during startup init_db: {e}")

