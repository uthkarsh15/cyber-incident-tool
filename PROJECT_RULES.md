# PROJECT_RULES.md — Master Rulebook
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-24 | VERSION: 1.0 -->

> **Purpose**: This file is the single source of truth for all project conventions, technology choices, coding standards, and constraints. Every AI model or developer working on this project **MUST read this file first** before writing any code.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | Indian Cyber Incident Intelligence Platform |
| **Synopsis Reference** | `Synopsis_CyberIncidentTool.md` |
| **SIH Problem ID** | 1677 (NTRO — Smart India Hackathon 2024) |
| **Goal** | Real-time, autonomous, India-specific cyber incident feed tool |
| **Target Users** | Government (CERT-In, NCIIPC), researchers, private sector SOCs |
| **License** | Open-source |

---

## 2. Definitive Technology Stack

> **RULE**: Use **exactly one** tool per job. Do NOT introduce alternatives unless explicitly approved.

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| **Language** | Python | 3.11+ | Core development language for all backend, ML, scraping |
| **API Framework** | FastAPI | latest stable | Async REST API with auto-docs (Swagger/ReDoc) |
| **ORM** | SQLAlchemy | 2.x | Async-compatible ORM for PostgreSQL |
| **Database** | PostgreSQL | 15+ | Structured incident storage, full-text search |
| **Migration** | Alembic | latest | Database schema versioning |
| **Web Scraping** | Scrapy | latest | Spider-based crawling for static pages |
| **Browser Automation** | Playwright (Python) | latest | JavaScript-rendered pages only |
| **NLP / ML** | HuggingFace Transformers, spaCy | latest | DistilBERT classification, NER |
| **Dashboard** | Streamlit | latest | Interactive real-time visualization |
| **Message Queue** | Redis | 7+ | Real-time ingestion pipeline, caching |
| **Containerization** | Docker + Docker Compose | latest | Deployment orchestration |
| **Version Control** | Git + GitHub | — | Source code management |
| **Environment Mgmt** | python-venv | — | Virtual environment (`.venv/`) |
| **Config Management** | pydantic-settings | latest | `.env` → typed settings |
| **Testing** | pytest + httpx | latest | Unit & integration tests |

### 2.1 Explicitly NOT Using
- ❌ MongoDB (using PostgreSQL only)
- ❌ Kafka (using Redis for simplicity in MVP)
- ❌ React/Grafana for dashboard (using Streamlit)
- ❌ LangChain/CrewAI/AutoGen (building lightweight custom agents; synopsis mentions these as options, we choose custom for control)
- ❌ Paid APIs of any kind
- ❌ Ollama/LLaMA/Mistral for MVP (phase 2 extension — classification uses fine-tuned DistilBERT)
- ❌ Go language (mentioned in context but not needed)

---

## 3. Project Structure

```
cyber-incident-tool/
│
├── PROJECT_RULES.md            ← YOU ARE HERE — read first
├── ARCHITECTURE.md             ← System design & component diagram
├── IMPLEMENTATION_PLAN.md      ← Phase-by-phase build order
├── DATA_MODELS.md              ← DB schemas, Pydantic models, API contracts
├── AGENT_DESIGN.md             ← Agent pipeline specifications
├── PROGRESS.md                 ← Living build tracker (update after each task)
├── Synopsis_CyberIncidentTool.md ← Original academic synopsis
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI app entry point
│   │   ├── config.py            ← Settings from .env via pydantic-settings
│   │   ├── database.py          ← SQLAlchemy engine, session, Base
│   │   │
│   │   ├── models/              ← SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── incident.py
│   │   │   ├── source.py
│   │   │   └── entity.py
│   │   │
│   │   ├── schemas/             ← Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── incident.py
│   │   │   └── source.py
│   │   │
│   │   ├── api/                 ← FastAPI route modules
│   │   │   ├── __init__.py
│   │   │   ├── incidents.py
│   │   │   ├── sources.py
│   │   │   └── feed.py
│   │   │
│   │   ├── agents/              ← Autonomous processing agents
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py
│   │   │   ├── scraper_agent.py
│   │   │   ├── relevance_agent.py
│   │   │   ├── classification_agent.py
│   │   │   ├── correlation_agent.py
│   │   │   ├── insight_agent.py
│   │   │   └── orchestrator.py
│   │   │
│   │   ├── services/            ← Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── incident_service.py
│   │   │   └── feed_service.py
│   │   │
│   │   └── utils/               ← Helpers, constants, shared functions
│   │       ├── __init__.py
│   │       ├── text_processing.py
│   │       └── india_filter.py
│   │
│   ├── tests/                   ← Backend test suite
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_agents.py
│   │   └── conftest.py
│   │
│   ├── alembic/                 ← Database migrations
│   │   └── versions/
│   │
│   ├── alembic.ini
│   └── requirements.txt
│
├── scraper/
│   ├── spiders/                 ← Scrapy spiders (one per source)
│   │   ├── __init__.py
│   │   ├── certin_spider.py
│   │   ├── news_spider.py
│   │   └── github_spider.py
│   ├── pipelines/               ← Scrapy item pipelines
│   │   ├── __init__.py
│   │   └── incident_pipeline.py
│   ├── items.py
│   ├── settings.py
│   └── scrapy.cfg
│
├── dashboard/
│   ├── app.py                   ← Streamlit main entry
│   ├── pages/                   ← Multi-page Streamlit app
│   │   ├── 1_Live_Feed.py
│   │   ├── 2_Analytics.py
│   │   └── 3_Heatmap.py
│   └── components/              ← Reusable Streamlit components
│       └── charts.py
│
├── ml/
│   ├── datasets/                ← Training data (CSV/JSON)
│   ├── training/                ← Training scripts
│   │   ├── train_classifier.py
│   │   └── train_ner.py
│   └── models/                  ← Saved model artifacts (.pt, config)
│
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.dashboard
├── .env                         ← Environment variables (NEVER commit secrets)
├── .env.example                 ← Template for .env
├── .gitignore
└── README.md
```

---

## 4. Coding Standards

### 4.1 Python Style
- **PEP 8** for all Python code
- **Type hints** on every function signature
- **Docstrings** on every public function (Google-style)
- Max line length: **120 characters**
- Use `pathlib.Path` instead of `os.path`
- Use f-strings for string formatting
- Imports order: stdlib → third-party → local (use `isort`)

### 4.2 Naming Conventions
| Thing | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `scraper_agent.py` |
| Classes | `PascalCase` | `IncidentClassifier` |
| Functions | `snake_case` | `classify_incident()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| DB Tables | `snake_case` (plural) | `incidents`, `sources` |
| API Endpoints | `/kebab-case` | `/api/v1/incidents` |
| Env Variables | `UPPER_SNAKE_CASE` | `DATABASE_URL` |

### 4.3 FastAPI Conventions
- All routes go in `backend/app/api/` as separate router modules
- Register routers in `main.py` with prefix `/api/v1`
- Use dependency injection for database sessions
- Return Pydantic schemas, never raw dicts
- Use HTTP status codes correctly (201 for create, 404 for not found, etc.)
- All endpoints must have `response_model` specified

### 4.4 Database Conventions
- Every table has: `id` (UUID primary key), `created_at`, `updated_at`
- Use Alembic for ALL schema changes — never modify DB directly
- Foreign keys use `<table_singular>_id` naming (e.g., `source_id`)
- Indexes on frequently queried columns (timestamps, categories)

### 4.5 Error Handling
- Use FastAPI `HTTPException` for API errors
- Agents must catch and log errors, never crash silently
- Use Python `logging` module (not `print()`)
- Log format: `%(asctime)s | %(name)s | %(levelname)s | %(message)s`

---

## 5. Environment & Configuration

### 5.1 Required Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cyber_incidents
DATABASE_URL_SYNC=postgresql://user:password@localhost:5432/cyber_incidents

# Redis
REDIS_URL=redis://localhost:6379/0

# App
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

# Scraper
SCRAPER_INTERVAL_MINUTES=30
SCRAPER_RATE_LIMIT_SECONDS=2
SCRAPER_USER_AGENT=CyberIncidentBot/1.0

# Dashboard
DASHBOARD_PORT=8501

# ML
MODEL_PATH=./ml/models
```

### 5.2 Config Loading Pattern
```python
# backend/app/config.py — ALWAYS use this pattern
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    app_env: str = "development"
    # ... etc

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 6. Git & Version Control Rules

- **Branch naming**: `feature/<name>`, `fix/<name>`, `phase/<N>`
- **Commit messages**: `<type>: <description>` (e.g., `feat: add incident model`, `fix: handle null sector`)
- **Never commit**: `.env`, `.venv/`, `__pycache__/`, `ml/models/*.pt`, `*.pyc`
- **Always commit**: `.env.example`, `requirements.txt`, migration files

---

## 7. Ethical & Legal Constraints

> [!CAUTION]
> These constraints are non-negotiable.

1. **No bypassing** anti-bot protections, CAPTCHAs, or access controls
2. **Respect** `robots.txt` on all crawled sites
3. **Rate limit** all scrapers (minimum 2-second delay between requests)
4. **No dark web crawling** in MVP (phase 2 extension only after legal review)
5. **No scraping** paywalled or login-protected content
6. **Attribute** all data sources in the feed output
7. **No paid APIs** — the system must be fully self-sufficient
8. **No storing** personal data (PII) — filter out before database insert

---

## 8. Testing Requirements

- **Unit tests** for every agent, service, and utility function
- **Integration tests** for API endpoints using `httpx.AsyncClient`
- **Test database** using SQLite in-memory for speed
- **Minimum coverage**: 70% before any phase is considered complete
- Run tests: `cd backend && pytest -v --tb=short`

---

## 9. Documentation Update Protocol

> [!IMPORTANT]
> After completing any task, the model/developer MUST update these files:

| File | When to Update |
|---|---|
| `PROGRESS.md` | After every completed task — mark status, add notes |
| `DATA_MODELS.md` | When any model, schema, or table changes |
| `ARCHITECTURE.md` | When any new component or service is added |
| `AGENT_DESIGN.md` | When any agent logic changes |
| `requirements.txt` | When any new package is installed |
| `README.md` | When setup steps or usage changes |

---

## 10. Build & Run Commands

```bash
# Setup (first time)
cd cyber-incident-tool
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r backend/requirements.txt

# Run backend API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run dashboard
cd dashboard
streamlit run app.py --server.port 8501

# Run tests
cd backend
pytest -v

# Database migrations
cd backend
alembic upgrade head            # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Docker (full stack)
docker-compose up --build
```
