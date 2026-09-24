# IMPLEMENTATION_PLAN.md — Phase-by-Phase Build Guide
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-24 | VERSION: 1.0 -->

> **Purpose**: Step-by-step build order with exact files to create and exact code to write. Each task is atomic — complete it fully before moving on. Read `PROJECT_RULES.md` first.

---

## Build Order Principles

1. **Each task produces runnable code** — no task leaves the project in a broken state
2. **Test after every task** — verify with `pytest` or manual check
3. **Update `PROGRESS.md`** after completing each task
4. **No skipping ahead** — tasks depend on previous tasks

---

## Phase 1: Project Foundation (Week 1)

> **Goal**: Working FastAPI app with database connection, health check, and config.

### Task 1.1: Environment & Dependencies

**What to do**:
1. Create `backend/requirements.txt` with all dependencies
2. Create `.env` with database credentials
3. Create `.env.example` as template
4. Create `.gitignore` with proper exclusions

**File: `backend/requirements.txt`**
```
# Core
fastapi==0.115.*
uvicorn[standard]==0.34.*
pydantic==2.*
pydantic-settings==2.*

# Database
sqlalchemy[asyncio]==2.*
asyncpg==0.30.*
psycopg2-binary==2.*
alembic==1.*

# Redis
redis==5.*

# HTTP
httpx==0.28.*

# Utilities
python-dotenv==1.*

# Testing
pytest==8.*
pytest-asyncio==0.*
httpx==0.28.*
```

**File: `.env`**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cyber_incidents
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/cyber_incidents
REDIS_URL=redis://localhost:6379/0
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
SCRAPER_INTERVAL_MINUTES=30
SCRAPER_RATE_LIMIT_SECONDS=2
```

**File: `.gitignore`**
```
.venv/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
ml/models/*.pt
ml/models/*.bin
*.db
.DS_Store
```

**Verify**: `pip install -r backend/requirements.txt` succeeds

---

### Task 1.2: Configuration Module

**What to do**: Create `backend/app/config.py` using pydantic-settings

**File: `backend/app/config.py`**
- Import `BaseSettings` from `pydantic_settings`
- Define all settings from `.env`
- Export singleton `settings` instance
- See `PROJECT_RULES.md` §5.2 for the pattern

**Verify**: `python -c "from app.config import settings; print(settings.app_env)"`

---

### Task 1.3: Database Connection

**What to do**: Create `backend/app/database.py` with async SQLAlchemy engine

**File: `backend/app/database.py`**
- Create async engine from `settings.database_url`
- Create `async_sessionmaker`
- Create `Base` declarative base
- Create `get_db()` dependency for FastAPI
- Create `init_db()` function that creates all tables

**Verify**: Import succeeds, `Base` is available

---

### Task 1.4: FastAPI App Setup

**What to do**: Update `backend/app/main.py` with CORS, lifespan, router registration

**File: `backend/app/main.py`**
- Add CORS middleware (allow all origins in dev)
- Add lifespan handler that calls `init_db()` on startup
- Register API routers with prefix `/api/v1`
- Keep root `/` and `/health` endpoints

**Verify**: `uvicorn app.main:app --reload` starts, visit `http://localhost:8000/docs`

---

### Task 1.5: Create `__init__.py` Files

**What to do**: Create empty `__init__.py` in every Python package directory

**Files to create** (all empty):
- `backend/app/__init__.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/agents/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/utils/__init__.py`

**Verify**: `python -c "import app"` succeeds from `backend/` directory

---

## Phase 2: Data Models & Database (Week 2)

> **Goal**: All database tables created, ORM models working, Alembic migrations set up.

### Task 2.1: SQLAlchemy ORM Models

**What to do**: Create all ORM models as specified in `DATA_MODELS.md` §3

**Files to create**:
- `backend/app/models/incident.py` — `Incident` model
- `backend/app/models/source.py` — `Source` model
- `backend/app/models/entity.py` — `Entity`, `IncidentEntity`, `Sector`, `Correlation` models

**File: `backend/app/models/__init__.py`** (import all models)
```python
from app.models.incident import Incident
from app.models.source import Source
from app.models.entity import Entity, IncidentEntity, Sector, Correlation
```

**Verify**: All models import without errors

---

### Task 2.2: Alembic Setup

**What to do**: Initialize Alembic, configure it, create initial migration

**Steps**:
```bash
cd backend
alembic init alembic
```
- Edit `alembic.ini`: set `sqlalchemy.url` from env
- Edit `alembic/env.py`: import `Base.metadata`, configure async
- Generate migration: `alembic revision --autogenerate -m "initial tables"`
- Apply: `alembic upgrade head`

**Verify**: Tables exist in PostgreSQL

---

### Task 2.3: Seed Data Script

**What to do**: Create a script to populate `sectors` and `sources` tables

**File: `backend/app/utils/seed.py`**
- Insert all 13 sectors from `DATA_MODELS.md` §7.1
- Insert 3 initial sources from `DATA_MODELS.md` §7.2
- Idempotent (skip if already exists)

**Verify**: Run seed script, check data in DB

---

### Task 2.4: Pydantic Schemas

**What to do**: Create all request/response schemas from `DATA_MODELS.md` §4

**Files to create**:
- `backend/app/schemas/incident.py`
- `backend/app/schemas/source.py`
- `backend/app/schemas/__init__.py` (exports)

**Verify**: Schemas instantiate with test data

---

## Phase 3: API Routes (Week 3)

> **Goal**: Full CRUD API for incidents and sources, feed endpoints.

### Task 3.1: Incident Service Layer

**What to do**: Create business logic for incident CRUD

**File: `backend/app/services/incident_service.py`**
- `create_incident(db, data: IncidentCreate) -> Incident`
- `get_incident(db, id: UUID) -> Incident | None`
- `list_incidents(db, filters, page, page_size) -> tuple[list[Incident], int]`
- `update_incident(db, id: UUID, data: IncidentUpdate) -> Incident`
- `delete_incident(db, id: UUID) -> bool`

**Verify**: Unit tests pass

---

### Task 3.2: Incident API Routes

**What to do**: Create FastAPI router for incidents

**File: `backend/app/api/incidents.py`**
- `GET /incidents` with query params: `page`, `page_size`, `attack_type`, `severity`, `date_from`, `date_to`
- `GET /incidents/{id}` with 404 handling
- `POST /incidents` with `IncidentCreate` body
- `PATCH /incidents/{id}` with `IncidentUpdate` body
- `DELETE /incidents/{id}`
- All use `response_model` parameter

**File: `backend/app/api/sources.py`**
- `GET /sources` — list all sources
- `POST /sources` — create new source

**Register both routers in `main.py`**

**Verify**: All endpoints work at `http://localhost:8000/docs`

---

### Task 3.3: Feed Generator

**What to do**: Create feed endpoints for external consumers

**File: `backend/app/api/feed.py`**
- `GET /feed/json` — returns last 50 incidents as JSON array
- `GET /feed/rss` — returns RSS 2.0 XML with latest incidents

**File: `backend/app/services/feed_service.py`**
- `generate_json_feed(db) -> list[dict]`
- `generate_rss_feed(db) -> str` (XML string)

**Verify**: Both `/api/v1/feed/json` and `/api/v1/feed/rss` return valid data

---

### Task 3.4: Statistics API

**What to do**: Aggregate queries for dashboard

**File: `backend/app/api/stats.py`** (new router)
- `GET /stats/overview` — total incidents, counts by severity, by type, by sector
- `GET /stats/trends` — daily incident counts for last 30 days

**Register in `main.py`**

**Verify**: Stats endpoints return correct aggregations

---

## Phase 4: Scrapy Spiders (Week 4–5)

> **Goal**: Working scraper for at least 2 sources, Redis queue integration.

### Task 4.1: Scrapy Project Setup

**What to do**: Initialize Scrapy project in `scraper/`

**Files to create**:
- `scraper/scrapy.cfg`
- `scraper/settings.py` — Scrapy settings (delays, user-agent, pipelines)
- `scraper/items.py` — `RawArticleItem` definition
- `scraper/spiders/__init__.py`

**Verify**: `cd scraper && scrapy list` shows no errors

---

### Task 4.2: CERT-In Spider

**What to do**: Build first spider for CERT-In advisories

**File: `scraper/spiders/certin_spider.py`**
- Follow structure from `AGENT_DESIGN.md` §2.3
- Extract advisory title, content, date, URL
- Handle pagination if applicable
- Respect rate limit (2s delay)

**Verify**: `scrapy crawl certin` outputs articles

---

### Task 4.3: News Spider (The Hacker News)

**What to do**: Build spider for The Hacker News

**File: `scraper/spiders/news_spider.py`**
- Parse article listing page
- Follow links to full articles
- Extract title, content, publish date, URL
- 2-second delay between requests

**Verify**: `scrapy crawl news` outputs articles

---

### Task 4.4: Redis Pipeline

**What to do**: Create Scrapy pipeline that pushes to Redis

**File: `scraper/pipelines/incident_pipeline.py`**
- Follow structure from `AGENT_DESIGN.md` §2.5
- Push JSON to `incident:raw` Redis list

**Update `scraper/settings.py`** to enable the pipeline

**Verify**: After crawl, `redis-cli LLEN incident:raw` shows items

---

## Phase 5: Agent Pipeline (Week 5–7)

> **Goal**: All 4 processing agents working, orchestrator consuming from Redis.

### Task 5.1: Base Agent

**File: `backend/app/agents/base_agent.py`**
- Implement `BaseAgent` from `AGENT_DESIGN.md` §1.1

---

### Task 5.2: Relevance Agent

**File: `backend/app/agents/relevance_agent.py`**
- Implement from `AGENT_DESIGN.md` §3
- India keyword matching + scoring
- Threshold-based filtering

**Verify**: Unit test with sample articles (India-related passes, unrelated fails)

---

### Task 5.3: Classification Agent

**File: `backend/app/agents/classification_agent.py`**
- Implement from `AGENT_DESIGN.md` §4
- Rule-based keyword matching for attack type, severity, sector

**Verify**: Unit test with sample articles produces correct classifications

---

### Task 5.4: Correlation Agent

**File: `backend/app/agents/correlation_agent.py`**
- Implement from `AGENT_DESIGN.md` §5
- URL deduplication
- Title similarity (Jaccard)
- Database queries for recent incidents

**Verify**: Unit test with duplicate and unique articles

---

### Task 5.5: Insight Agent

**File: `backend/app/agents/insight_agent.py`**
- Implement from `AGENT_DESIGN.md` §6
- spaCy NER extraction
- CVE/IP regex extraction
- Database persistence

**Add to requirements**: `spacy` and run `python -m spacy download en_core_web_sm`

**Verify**: End-to-end test: article → entities extracted → saved to DB

---

### Task 5.6: Pipeline Orchestrator

**File: `backend/app/agents/orchestrator.py`**
- Implement from `AGENT_DESIGN.md` §1.2 and §8.1
- Redis consumer loop
- Sequential agent pipeline execution
- Error handling and logging

**Verify**: Push test article to Redis → orchestrator processes → incident appears in DB

---

## Phase 6: Streamlit Dashboard (Week 8–9)

> **Goal**: Interactive dashboard with live feed, analytics, and heatmap pages.

### Task 6.1: Dashboard Structure

**Files to create**:
- `dashboard/app.py` — Streamlit main page (overview)
- `dashboard/pages/1_Live_Feed.py` — Real-time incident table with filters
- `dashboard/pages/2_Analytics.py` — Charts: attack type distribution, severity, timeline
- `dashboard/pages/3_Heatmap.py` — Sector vulnerability visualization
- `dashboard/components/charts.py` — Reusable chart functions
- `dashboard/requirements.txt` — Streamlit + plotly + requests

**Verify**: `streamlit run dashboard/app.py` shows working dashboard

---

### Task 6.2: API Integration

**What to do**: Dashboard fetches data from FastAPI endpoints

- Live Feed page calls `GET /api/v1/incidents`
- Analytics page calls `GET /api/v1/stats/overview` and `GET /api/v1/stats/trends`
- Heatmap page calls `GET /api/v1/stats/overview` (sector breakdown)

**Verify**: Dashboard displays real incident data from database

---

## Phase 7: Docker & Deployment (Week 10)

> **Goal**: Full stack runs with `docker-compose up`.

### Task 7.1: Dockerfiles

**Files to create**:
- `Dockerfile.backend` — Python 3.11, install requirements, run uvicorn
- `Dockerfile.dashboard` — Python 3.11, install requirements, run streamlit

---

### Task 7.2: Docker Compose

**File: `docker-compose.yml`**
- Services: `backend`, `dashboard`, `postgres`, `redis`
- Volumes for persistent DB storage
- Network linking
- Health checks

**Verify**: `docker-compose up --build` starts all services

---

## Phase 8: ML Models (Week 11–14)

> **Goal**: Fine-tuned DistilBERT classifier replaces rule-based classification.

### Task 8.1: Dataset Curation

**File: `ml/datasets/README.md`** — Document dataset format
- Collect labeled cyber incident data (CERT-In reports, news articles)
- CSV format: `title`, `content`, `attack_type`, `severity`, `sector`
- Minimum 500 labeled samples for initial training

---

### Task 8.2: DistilBERT Training

**File: `ml/training/train_classifier.py`**
- Fine-tune `distilbert-base-uncased` for multi-label classification
- Train/validation split: 80/20
- Save model to `ml/models/incident_classifier/`

---

### Task 8.3: NER Model Training

**File: `ml/training/train_ner.py`**
- Fine-tune spaCy NER or use HuggingFace token classification
- Entity types: organization, threat_actor, cve_id, ip_address, software

---

### Task 8.4: Agent Integration

- Update `ClassificationAgent` to use trained model
- Update `InsightAgent` to use trained NER model
- Keep rule-based as fallback

---

## Phase 9: Testing & Documentation (Week 15–18)

> **Goal**: Comprehensive tests, documentation, final polish.

### Task 9.1: Test Suite

**Files to create**:
- `backend/tests/conftest.py` — Fixtures, test DB setup
- `backend/tests/test_api.py` — API endpoint tests
- `backend/tests/test_agents.py` — Agent unit tests
- `backend/tests/test_services.py` — Service layer tests

**Target**: 70%+ code coverage

---

### Task 9.2: README

**File: `README.md`** — Complete project README
- Project description
- Architecture diagram
- Setup instructions (local + Docker)
- API documentation link
- Screenshots of dashboard

---

### Task 9.3: Performance Evaluation

- Measure classification accuracy (F1-score)
- Measure scraper coverage (sources × frequency)
- Measure API latency (p50, p95, p99)
- Document results in `PROGRESS.md`
