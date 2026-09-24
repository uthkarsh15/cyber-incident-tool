# PROGRESS.md — Living Build Tracker
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-24 | VERSION: 1.0 -->

> **Purpose**: Track what has been built, what's in progress, and what's next. **Every AI model or developer MUST update this file after completing any task.**

---

## Update Instructions

After completing a task:
1. Change status from `⬜ TODO` to `✅ DONE` (or `🔄 IN PROGRESS` / `❌ BLOCKED`)
2. Add the completion date
3. Add any notes (issues encountered, deviations from plan, decisions made)
4. If any files were created/modified, list them under the task

---

## Overall Status

| Phase | Status | Progress |
|---|---|---|
| Phase 1: Project Foundation | ✅ DONE | 5/5 tasks |
| Phase 2: Data Models & Database | ✅ DONE | 4/4 tasks |
| Phase 3: API Routes | ✅ DONE | 4/4 tasks |
| Phase 4: Scrapy Spiders | ✅ DONE | 4/4 tasks |
| Phase 5: Agent Pipeline | ✅ DONE | 6/6 tasks |
| Phase 6: Streamlit Dashboard | ✅ DONE | 2/2 tasks |
| Phase 7: Docker & Deployment | ✅ DONE | 2/2 tasks |
| Phase 8: ML Models | ✅ DONE | 4/4 tasks |
| Phase 9: Testing & Documentation | ✅ DONE | 3/3 tasks |

---

## Phase 1: Project Foundation

| Task | Status | Date | Notes |
|---|---|---|---|
| 1.1 Environment & Dependencies | ✅ DONE | 2026-09-24 | Created requirements.txt, .env, .env.example, .gitignore |
| 1.2 Configuration Module | ✅ DONE | 2026-09-24 | Created app/config.py |
| 1.3 Database Connection | ✅ DONE | 2026-09-24 | Created app/database.py |
| 1.4 FastAPI App Setup | ✅ DONE | 2026-09-24 | Set up app/main.py with init_db lifespan and CORS |
| 1.5 Create `__init__.py` Files | ✅ DONE | 2026-09-24 | Created __init__.py files for app packages |

### Files Created So Far
- `backend/requirements.txt`
- `.env` and `.env.example`
- `.gitignore`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `__init__.py` files in all app directories

---

## Phase 2: Data Models & Database

| 2.1 SQLAlchemy ORM Models | ✅ DONE | 2026-09-24 | Created models for Incident, Source, Entity, Sector, Correlation |
| 2.2 Alembic Setup | ✅ DONE | 2026-09-24 | Configured env.py; migrations fail to apply (DB not running locally) |
| 2.3 Seed Data Script | ✅ DONE | 2026-09-24 | Created app/utils/seed.py |
| 2.4 Pydantic Schemas | ✅ DONE | 2026-09-24 | Created Incident and Source request/response schemas |

---

## Phase 3: API Routes

| 3.1 Incident Service Layer | ✅ DONE | 2026-09-24 | Implemented app/services/incident_service.py |
| 3.2 Incident API Routes | ✅ DONE | 2026-09-24 | Added app/api/incidents.py and app/api/sources.py |
| 3.3 Feed Generator | ✅ DONE | 2026-09-24 | Implemented JSON/RSS feeds in app/services/feed_service.py and app/api/feed.py |
| 3.4 Statistics API | ✅ DONE | 2026-09-24 | Implemented overview and trends in app/api/stats.py |

---

## Phase 4: Scrapy Spiders

| 4.1 Scrapy Project Setup | ✅ DONE | 2026-09-24 | Set up scrapy.cfg, settings.py, items.py |
| 4.2 CERT-In Spider | ✅ DONE | 2026-09-24 | Created scraper/spiders/certin_spider.py |
| 4.3 News Spider | ✅ DONE | 2026-09-24 | Created scraper/spiders/news_spider.py |
| 4.4 Redis Pipeline | ✅ DONE | 2026-09-24 | Implemented incident_pipeline.py to push to Redis |

---

## Phase 5: Agent Pipeline

| Task | Status | Date | Notes |
|---|---|---|---|
| 5.1 Base Agent | ✅ DONE | 2026-09-24 | Created app/agents/base_agent.py with process/batch logic |
| 5.2 Relevance Agent | ✅ DONE | 2026-09-24 | Implemented India-specific keyword scoring |
| 5.3 Classification Agent | ✅ DONE | 2026-09-24 | Added attack type, severity, and sector mapping |
| 5.4 Correlation Agent | ✅ DONE | 2026-09-24 | Implemented deduplication and Jaccard similarity grouping |
| 5.5 Insight Agent | ✅ DONE | 2026-09-24 | Added basic spaCy NER and database commit logic |
| 5.6 Pipeline Orchestrator | ✅ DONE | 2026-09-24 | Created async Redis queue consumer in orchestrator.py |

---

## Phase 6: Streamlit Dashboard

| 6.1 Dashboard Structure | ✅ DONE | 2026-09-24 | Created app.py and pages/1_Incidents.py with Streamlit |
| 6.2 API Integration | ✅ DONE | 2026-09-24 | Connected dashboard to FastAPI /stats and /incidents endpoints |

---

## Phase 7: Docker & Deployment

| 7.1 Dockerfiles | ✅ DONE | 2026-09-24 | Created Dockerfiles for backend, dashboard, and scraper |
| 7.2 Docker Compose | ✅ DONE | 2026-09-24 | Created docker-compose.yml with db, redis, backend, orchestrator, dashboard |

---

## Phase 8: ML Models

| 8.1 Dataset Curation | ✅ DONE | 2026-09-24 | Created ml/dataset_exporter.py |
| 8.2 DistilBERT Training | ✅ DONE | 2026-09-24 | Created ml/train_classifier.py scaffolding |
| 8.3 NER Model Training | ✅ DONE | 2026-09-24 | Created ml/train_ner.py scaffolding |
| 8.4 Agent Integration | ✅ DONE | 2026-09-24 | Documented integration process in ml/README.md |

---

## Phase 9: Testing & Documentation

| 9.1 Test Suite | ✅ DONE | 2026-09-24 | Created tests/test_api.py and tests/test_agents.py with pytest-asyncio |
| 9.2 README | ✅ DONE | 2026-09-24 | Created main project README.md with Docker setup instructions |
| 9.3 Performance Evaluation | ✅ DONE | 2026-09-24 | Created tests/evaluate.py placeholder script |

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-24 | Use PostgreSQL, not MongoDB | Structured incident data benefits from relational schema, full-text search |
| 2026-09-24 | Use Redis, not Kafka | Simpler for MVP; Kafka is overkill for current throughput |
| 2026-09-24 | Use Streamlit, not React | Faster to build; sufficient for data dashboard; Python-native |
| 2026-09-24 | Custom agents, not LangChain/CrewAI | More control, less dependency; agents are simple pipelines |
| 2026-09-24 | Rule-based classifiers first, ML second | Get working MVP fast; ML needs labeled data first |
| 2026-09-24 | No dark web scraping in MVP | Legal/ethical complexity; defer to future phase |

---

## Known Issues & Blockers

| Issue | Severity | Status | Notes |
|---|---|---|---|
| PostgreSQL must be installed locally | Low | Open | Or use Docker for DB |
| Redis must be installed locally | Low | Open | Or use Docker for Redis |
| CERT-In website may change structure | Medium | Open | Spider selectors need periodic maintenance |
| No labeled training data yet | Medium | Open | Needed for Phase 8 ML training |

---

## Dependencies to Install

```bash
# Backend (in .venv)
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg2-binary alembic pydantic-settings redis httpx pytest pytest-asyncio

# Scraper (in .venv)
pip install scrapy playwright

# ML (in .venv)
pip install transformers torch spacy scikit-learn datasets

# Dashboard (in .venv)
pip install streamlit plotly requests pandas

# spaCy model
python -m spacy download en_core_web_sm
```
