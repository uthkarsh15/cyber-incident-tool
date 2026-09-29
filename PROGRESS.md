# PROGRESS.md — Living Build Tracker
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-29 | VERSION: 1.2 -->

> **Purpose**: Track what has been built, what's in progress, and what's next. **Every AI model or developer MUST update this file after completing any task.**

---

> ⚠️ **VERIFICATION NOTICE (2026-09-29, Stage 0 audit)** — Every `✅ DONE` mark below this notice is an **UNVERIFIED CLAIM** written by a prior AI session on 2026-09-24 that never ran any command. Per project rules, nothing counts as DONE until a successful command proves it. Stage 0 below records the *only* items that have actually been verified as of today.

---

## Stage E — End-to-end Pipeline Trace (Option A) (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| E.1 Pre-flight audit (git / Redis / Docker / PG / STATUS.md claims vs reality | ✅ VERIFIED | `git log`, `git status`, `redis-cli LLEN`, `docker ps`, psql UNION + incidents SELECT | Reality contradicted STATUS.md: 2 corrupted rows existed (not 1 preview claimed); 1 had empty title; both source_id=NULL and published_at=NULL; API returned 500 MetaData() validation error. All docs had not been updated. |
| E.2 Root cause of 3 pipeline bugs identified | ✅ VERIFIED | Read incident.py model/schema, incident_service, insight_agent | (1) metadata column: ORM attr `metadata_` vs schema name `metadata` → Pydantic reads SQLAlchemy MetaData() object, not JSONB dict. (2) source_id never looked up by insight_agent. (3) published_at never passed nor parsed from date string format. |
| E.3 3 pipeline bugs fixed (schema/service + agent code edits applied) | ✅ VERIFIED | python -m compileall backend/app -q → exit 0; docker compose build backend agent_orchestrator → Built both built; docker exec backend pytest 5/5 PASSED | 3 files, 51 insertions, 6 deletions. pytest 0 regressions. |
| E.4 Clean state before trace | ✅ VERIFIED | redis-cli DEL incident:raw → LLEN=0; psql DELETE incidents/entities/IE/correlations; 0 rows; 3 sources 13 sectors preserved; orchestrator Exited before scrape (so spider runs independent proof | ✅ VERIFIED | `docker stop agent_orchestrator; docker run --network cyber-incident-tool_default scrapy crawl news -s CLOSESPIDER_ITEMCOUNT=1; redis-cli LLEN=16 | LLEN=16 | Scrapy CLOSESPIDER_ITEMCOUNT bulk yields 16 items then cap registers. |
| E.6 Queue pruned to 1 India-relevant item | ✅ VERIFIED | Per-item LINDEX + python relevance scoring of 16 items; 0-15; LPOP x6; LTRIM 0; post: LLEN=1; idx=6 Weekly 0.60 passes filter (1 of 16 real scraped articles passes threshold 0.40 |
| E.7 Orchestrator consumes single item through 4 agents | ✅ VERIFIED | docker start agent_orchestrator; docker logs tail 50 → INSERT INTO incidents + entities; redis-cli LLEN goes → 0. All rows → 0. relevance: kept score 0.60; classification: attack_type=ransomware severity=critical confidence=1.0 sector=government; correlation: no dedup (firstitem; insight: 61x CVE entities, committed incident e163c9f8 committed. |
| E.8 Postgres ground truth after trace | ✅ VERIFIED | psql UNION COUNT query | incidents=1, entities=61 cve_id, incident_entities=61, correlations=0 | Incident row SELECT: source_name='The Hacker News' source_id FK NOT NULL; published_at='2026-09-28 parsed correctly; metadata `metadata {} dict NOT NULL title populated; attack_type ransomware; sector government; all 11 fields correct. |
| E.9 API returns 200 with real incident data (fixed 500) | ✅ VERIFIED | curl :8000/api/v1/incidents → HTTP 200 total=1. curl /incidents/{id} → HTTP 200; metadata=dict(keys=[]) not MetaData() error 200 OK; 13 fields in list endpoint; same shape matches PG values. MetaData() validation error eliminated. |
| E.10 Test suite 0 regressions | ✅ VERIFIED | docker exec backend python -m pytest -v → 5/5 PASSED 1.54s | Coverage 47% overall (dropped 3%; insight_agent grew ~30 untested; gap still <70% documented decision needed → gap <70%. |

---

## Stage D — Scraping (VERIFIED 2026-09-29)

| Item | Status | Proof command | Notes |
|---|---|---|---|
| D.1 Environment: Scrapy runs | ✅ VERIFIED | `docker build -t cyber-incident-scraper ./scraper` → build OK; `docker run --network cyber-incident-tool_default -e REDIS_URL=redis://redis:6379/0 … scrapy crawl …` | Host Python 3.14 sandbox blocks pip (WinError 5); ran inside scraper image (py3.11-slim, installed scrapy + redis via scraper/requirements.txt) |
| D.2 Rate limiting + robots obeyed | ✅ VERIFIED | `DOWNLOAD_DELAY=2, CONCURRENT_REQUESTS_PER_DOMAIN=1, ROBOTSTXT_OBEY=True` in settings.py; stats log `robotstxt/request_count=1`, elapsed ≈ 42s for 17 user requests → ~2.5s avg between requests | Ethical rule PROJECT_RULES §7 items 1–3 all satisfied |
| D.3 news_spider runs against THN | ✅ VERIFIED | `scrapy crawl news -s CLOSESPIDER_ITEMCOUNT=5` → stats: `item_scraped_count=16`, `finish_reason=closespider_itemcount`, `downloader/response_status_count/200=18`, 0 HTTP error codes, `elapsed_time_seconds=41.8` | |
| D.4 Items have non-empty title, date, content | ✅ VERIFIED | Redis LINDEX 0..2 sample: titles "Lunex Stealer … / Citrix NetScaler RCE … / CISA Says …", dates "Sep 26/27/28, 2026", content lengths 6330, 6574, 5427 chars | Two selector bugs fixed in this stage: (1) title was empty because h1 wraps an <a>; switched to `h1.story-title ::text` descendants + og:title fallback. (2) date got author name because `span.author` has multiple occurrences and `.get()` returned author only; switched to combined `.getall()` pool across 6 selectors + month/day/year regex. |
| D.5 Items pushed to Redis `incident:raw` list, RPUSH-style | ✅ VERIFIED | Before run: `DEL incident:raw` → 0; after news run: `LLEN incident:raw` = **16**. Orchestrator kept stopped to prevent race. Sample items validated as JSON with all expected 7 keys. | Pipeline bug fixed: hardcoded `host=localhost` → `REDIS_URL` env var parsed with `urlparse`; default `redis://localhost:6379/0`. |
| D.6 certin_spider (CERT-In) runs without Python errors | ✅ VERIFIED (0 items, site limitation) | Run 1: HTTP 200 on start_url VLNLIST, scheduler/dequeued=1 (start URL only), items=0. Run 2: TCP ConnectionRefused 111 x4 (site rate-limited/blocked our IP after first run; twisted-level, no Python exception). | Root cause of 0 items not code bugs: (1) old pageid PUBVLNOTES01 returns "page not available" — got real opcodes via site-JS `getOpcode()`: Vulnerabilities=VLNLIST, Advisories=PUBADVLIST; updated start_url. (2) VLNLIST static DOM only contains year headings ("2026 / 2025 …"); individual rows under each year are client-side JS-expanded/XHR-loaded, absent in Scrapy HTML. CERT-In spider needs Playwright to yield rows; no code changes this stage beyond pageid + robust parser. |
| D.7 PROJECT_RULES §3 mentions `github_spider.py` | ⚠️ NOT CREATED (missing in paste, not in this stage) | `Glob **/github_spider.py` → 0 results found | Noted, not blocking. Seed.py already lists BleepingComputer as 3rd source option. |
| D.8 Scrapy deprecation warnings cleaned | ✅ VERIFIED | Pipeline migrated to `from_crawler(cls, crawler)` pattern; lifecycle methods no longer require `spider` arg. | Old warnings (3): `open_spider / close_spider / process_item require spider argument, deprecated` — eliminated. |
| D.9 Pipeline fix was necessary & REDIS_URL env works | ✅ VERIFIED | Before: container `localhost` → would not reach redis service. After edit + rebuild: items land in shared-compose Redis instance at `redis:6379` and LLEN confirms them. | |
| D.10 Duplicate root `tests/` dir cleanup committed | ✅ VERIFIED (Stage 0 finding resolved) | Deleted: `tests/{conftest,evaluate,test_agents,test_api}.py`. Canonical suite remains `backend/tests/` (used by `cd backend && pytest` inside the backend image). | Stage C previously mirror-edited both copies to avoid drift; now only backend/tests remains. |
| D.11 ⚡ Stage E preview (accidental, not a proof here) | ℹ️ NOT CLAIMED, logged for future | First news run (16 items) consumed by still-running orchestrator. Post-run psql: incidents=1, entities=61, incident_entities=61. Orchestrator logs show real CVE INSERTs + COMMITs. | NOT a Stage D deliverable; only proves "the full pipeline path" works. Stage E will redo this cleanly end-to-end. |

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
