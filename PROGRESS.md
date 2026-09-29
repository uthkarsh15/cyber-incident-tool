# PROGRESS.md — Living Build Tracker
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-29 | VERSION: 1.1 -->

> **Purpose**: Track what has been built, what's in progress, and what's next. **Every AI model or developer MUST update this file after completing any task.**

---

> ⚠️ **VERIFICATION NOTICE (2026-09-29, Stage 0 audit)** — Every `✅ DONE` mark below this notice is an **UNVERIFIED CLAIM** written by a prior AI session on 2026-09-24 that never ran any command. Per project rules, nothing counts as DONE until a successful command proves it. Stage 0 below records the *only* items that have actually been verified as of today.

---

## Stage C — Tests (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| C.1 pytest suite runs | ✅ VERIFIED | `docker exec backend python -m pytest -v --tb=short` → exit 0, 5 passed in 1.17s | Host Python 3.14 sandbox blocked greenlet pip install; ran inside backend container (has all deps via requirements.txt) |
| C.2 Every test name + status listed | ✅ VERIFIED | Exact names in STATUS.md Stage C entry | test_relevance_agent_high_score ✅, test_relevance_agent_low_score ✅, test_root_endpoint ✅, test_health_endpoint ✅, test_get_incidents_empty ✅ — 5/5 PASSED |
| C.3 Import-error pre-fix catalogued | ✅ VERIFIED | `pytest` before fix → 1 collection error: `ModuleNotFoundError: No module named 'backend'` | test_agents.py used non-existent `from backend.app.agents…` inside container (package name is `app.agents…`) |
| C.4 Root-cause fix (not symptom/weakening) | ✅ VERIFIED | Edited 2 lines only: backend/tests/test_agents.py#L2, tests/test_agents.py#L2 | `from backend.app.agents.relevance_agent` → `from app.agents.relevance_agent`. No tests deleted/skipped/weakened. |
| C.5 0 skipped tests | ✅ VERIFIED | No SKIPPED rows in output; source of test_*.py inspected for @pytest.mark.skip → none | All 5 collected tests actually ran and asserted. |
| C.6 Coverage measured explicitly with --cov | ✅ VERIFIED | `docker exec backend python -m pytest --cov=app --cov-report=term-missing` → **overall 50% (609 stmts / 307 miss)** | ⚠️ Below 70% required in PROJECT_RULES.md §8. Noted. |
| C.7 Coverage gaps catalogued | ✅ VERIFIED | 14 modules at 0%: classification_agent, correlation_agent, insight_agent, orchestrator, seed.py (+ empty stubs scraper_agent, visualization_agent vacuously 100%) | Poor coverage: feed_service 26%, incident_service 30%, stats 48%, sources 61%, incidents route 64% |
| C.8 Untested major components flagged | ✅ VERIFIED | Audit in STATUS.md Stage C → 14-row table | Models (SQL behaviour), scraper package, migrations, dashboard, seed.py, all other agents → **ZERO dedicated tests**. Only relevance_agent + root/health/GET_incidents routes tested. |
| C.9 Decision on 70% rule | ⚠️ PENDING (your call) | Current 50% → either (a) write minimal targeted suite to bridge gap before Stage D, or (b) defer 70% to Stage G and proceed to D with coverage gap acknowledged | Recommended: proceed to D; coverage additions can land in parallel step after Stage E pipeline works end-to-end |

---

## Stage B — Database seed (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| B.1 Seed script located | ✅ VERIFIED | `Glob **/*seed*.py` → 1 result: backend/app/utils/seed.py | None in ml/; scripts/ dir doesn't exist |
| B.2 Seed runs cleanly against live DB | ✅ VERIFIED | `docker exec backend python -m app.utils.seed` → exit 0, "Database seeded successfully." | 13 sector INSERTs + 3 source INSERTs + 1 COMMIT visible in echo output |
| B.3 DB counts: sectors=13, sources=3, incidents=0 | ✅ VERIFIED | `docker exec db psql -c "SELECT 'sectors',COUNT(*) UNION ALL ..."` → sectors=13 sources=3 incidents=0 entities=0 | Seed script has ZERO incident rows (intentional) |
| B.4 Sectors & sources sample rows match seed data | ✅ VERIFIED | psql SELECT code,name FROM sectors → 13 rows exactly matching SEED_SECTORS; sources → 3 rows matching SEED_SOURCES with is_active=t | UUIDs stable, URLs correct, source_types correct |
| B.5 Seed idempotent on re-run | ✅ VERIFIED | Second `python -m app.utils.seed` → 0 new INSERTs; post-re-run counts still 13/3 | SELECT-then-skip-insert logic works |
| B.6 API /sources returns seeded data | ✅ VERIFIED | `curl :8000/api/v1/sources` → 3 objects HTTP 200; ids match psql sample exactly | response_model=list[SourceResponse] works |
| B.7 API /incidents still returns valid empty schema (0 rows expected) | ✅ VERIFIED | `curl :8000/api/v1/incidents` → `{"total":0,"page":1,"page_size":20,"incidents":[]}` | Correct — seed has no incidents |
| B.8 Stats endpoint exercises seeded sectors | ✅ VERIFIED | `curl :8000/api/v1/stats/overview` → by_sector lists all 13 sector names with count 0 | sectors+stats join path proven end-to-end |
| B.9 ⚠️ No incident seed rows provided by shipped script | ⚠️ NOTED (not blocked, needs your call) | source of seed.py — SEED_SECTORS + SEED_SOURCES only, no Incident data | /incidents can only show non-empty after a hand-written seed-incidents insert OR after Stage D scraping. Recommend: proceed to Stage C (pytest uses in-memory SQLite, doesn't need seeded PG) |

---

## Stage A — Run the stack (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| A.1 All 5 containers up, no crash loops | ✅ VERIFIED | `docker ps --format table` → 5 services Up, none Restarting | db (healthy), redis, backend, agent_orchestrator, dashboard |
| A.2 Alembic initial migration applied | ✅ VERIFIED | `docker exec db psql -c "\dt"` → 7 tables + alembic_version | `Running upgrade -> 90218464f447, initial tables` in backend logs |
| A.3 FastAPI /docs loads | ✅ VERIFIED | `curl -s -o NUL -w "%{http_code}" :8000/docs` → 200 | /health, /, /openapi.json, /api/v1/incidents all 200 |
| A.4 FastAPI /api/v1/incidents returns valid JSON | ✅ VERIFIED | `curl :8000/api/v1/incidents` → `{"total":0,...,"incidents":[]}` | Empty is OK pre-seed |
| A.5 Streamlit dashboard loads | ✅ VERIFIED | `curl :8501/_stcore/health` → 200 `ok`; `/` → 200 HTML | Streamlit poll-based watcher active (WSL) |
| A.6 Orchestrator starts, no import crashes | ✅ VERIFIED | `docker logs agent_orchestrator` → `Starting orchestrator queue consumer...` | Graceful `Spacy not installed` WARN only (intentional, regex fallback) |
| A.7 ⚠️ No scraper/scheduler service | ⚠️ GAP (reported, not fixed here) | `docker compose config` services list | Only db/redis/backend/agent_orchestrator/dashboard defined. scraper/Dockerfile exists but not used. SCRAPER_INTERVAL_MINUTES orphaned. Orchestrator BLPO on empty queue forever. |

---

## Stage 0 — Freeze & Inspect (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| 0.1 No syntax errors in any Python file | ✅ VERIFIED | `python -m compileall backend scraper dashboard ml tests -q` → exit 0, no output | Paste damage at grammar level (truncation, indent, smart quotes) ruled out. |
| 0.2 File structure reviewed against spec | ✅ VERIFIED | `git ls-files` compared line-by-line to PROJECT_RULES.md §3 | Findings: 5 files missing, scraper/ double-nested, tests/ duplicated, 3 extra tracked files, 2 ML files flat not in training/ |
| 0.3 `__init__.py` in all package dirs | ✅ VERIFIED | `LS` of backend/app/{api,agents,models,schemas,services,utils} and scraper/scraper/{pipelines,spiders} | All present ✅ |
| 0.4 Git baseline captured | ✅ VERIFIED | `git log --oneline -10` + `git status` | 2 commits total (generic labels); HANDOFF.md modified locally; no secrets leaking in git status |

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
