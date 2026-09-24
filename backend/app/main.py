from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.api import incidents, sources, feed, stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Indian Cyber Incident Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "Cyber Incident Intelligence API is running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }