# STATUS.md — Stage-by-Stage Verification Log

## Stage C — Tests
**Date**: 2026-09-29
**What was verified and how**:
- Environment: Host Python 3.14 sandbox blocks pip install of `greenlet` dist-info (WinError 5). Worked around by running the test suite inside the already-built `cyber-incident-tool-backend-1` Docker container (`/usr/local/bin/python` 3.11.16), which has all backend requirements.txt deps installed (including `sqlalchemy[asyncio]` → greenlet). pytest-cov was installed at test time in-container.
- Test execution command: `docker exec cyber-incident-tool-backend-1 python -m pytest -v --tb=short --cov=app --cov-report=term-missing`.
- **Pre-fix state (5 tests collected, 1 error at collection)**:
  - ERROR collecting tests/test_agents.py — `ModuleNotFoundError: No module named 'backend'` on line `from backend.app.agents.relevance_agent import RelevanceAgent`.
  - Root cause: paste damage / path mismatch. Inside backend image, PYTHONPATH is `/app` so package is `app.agents…`, not `backend.app.agents…`. The `backend/tests/conftest.py` adds ROOT_DIR hoping to import `backend.*`, but `/app` is the backend dir itself, not a child of it.
  - Classification: **real bug in test_agents.py import path**, not an app bug. Rule says fix root cause, not symptom.
  - Fix applied: edit `backend/tests/test_agents.py` line 2 `from backend.app.agents.relevance_agent` → `from app.agents.relevance_agent`. Mirror edit also applied to duplicate root `tests/test_agents.py` (which has identical contents and same bug; Stage 0 flagged the directory as paste duplicate — keeping both for now, fixing both to avoid drift).
- **Post-fix suite output (every test name listed)**:
  1. `tests/test_agents.py::test_relevance_agent_high_score PASSED`
  2. `tests/test_agents.py::test_relevance_agent_low_score PASSED`
  3. `tests/test_api.py::test_root_endpoint PASSED`
  4. `tests/test_api.py::test_health_endpoint PASSED`
  5. `tests/test_api.py::test_get_incidents_empty PASSED`
  Summary: **5 passed in 1.17s**. Exit code 0.
- **Skipped tests**: 0. No `SKIPPED` rows in output; inspected source of both test files — no `@pytest.mark.skip` / `skipif` / `xfail`. Nothing is skipped legitimately or otherwise. Every collected test ran.
- **Coverage (--cov=app --cov-report=term-missing actual output)**:
  | Category | Value |
  |---|---|
  | Total statements | 609 |
  | Missed statements | 307 |
  | **OVERALL COVERAGE** | **50%** ⚠️ **Below 70% PROJECT_RULES.md §8 requirement** |
  Modules at 0% coverage (14): `classification_agent.py` (28 stmt), `correlation_agent.py` (52), `insight_agent.py` (73), `orchestrator.py` (40), `seed.py` (21), plus empty modules `scraper_agent.py`, `visualization_agent.py` (0 stmts each, 100% vacuous — ignored for gap analysis).
  Poor coverage but non-zero: `feed_service.py` 26%, `incident_service.py` 30%, `stats.py` 48%, `sources.py` 61%, `incidents.py` 64%, `base_agent.py` 62%, `database.py` 71%, `feed.py` 75%.
  Well covered: `relevance_agent.py` 100%, all models (`entity/incident/source/__init__.py`) 100%*, all schemas (`incident/source/__init__.py`) 100%*, `config.py` 100%, `main.py` 90%. *(Models and schemas are 100% covered via import-time execution + incident route test loading the schema response model — no model-specific behavioural assertions exist, only indirect coverage.)*
- **Untested-major-components audit (flags for later stages)**:
  | Component | Test presence? | Gap |
  |---|---|---|
  | relevance_agent | ✅ 2 tests, 100% | — |
  | classification_agent | ❌ 0 tests, 0% | Stage D/E integration or test needed |
  | correlation_agent | ❌ 0 tests, 0% | Stage D/E integration or test needed |
  | insight_agent | ❌ 0 tests, 0% | Stage D/E integration or test needed |
  | orchestrator Redis BLPOP loop | ❌ 0 tests, 0% | Needs mocked Redis or Stage E pipeline test |
  | FastAPI routes except root/health/GET incidents | ⚠️ indirect | POST/PATCH/DELETE incidents, /sources, /stats, /feed only covered by import-time → 0-48% |
  | incident_service CRUD functions (create/update/delete/get) | ⚠️ 26% only | list_incidents hit via mock in test_get_incidents_empty; others untested |
  | Models (SQL behaviour: relationships, FK cascade, UUID defaults, constraint validation) | ❌ 0 unit tests | Only import-time coverage; no SQLite test exercises SQL logic |
  | Scrapy project (spiders, pipelines, middlewares) | ❌ 0 pytest anywhere for scraper package | No test_*.py in scraper/ at all |
  | seed.py | ❌ 0 tests, 0% covered | Stage B ran it manually; no automated assert |
  | Alembic migrations | ❌ 0 tests | Stage A ran it against PG; no auto test |
  | Dashboard / Streamlit | ❌ 0 tests | Not in pytest scope; Streamlit tests are separate story |
  | Duplicate root tests/ directory | ⚠️ Untouched but identical content | Same 3 files as backend/tests; not run by backend pytest; Stage D decision needed |
**What changed (only Stage C code edits)**:
1. [backend/tests/test_agents.py](file:///d:/cyber-incident-tool/backend/tests/test_agents.py#L2) line 2 — `from backend.app.agents…` → `from app.agents…` (fixes test import path for container execution).
2. Mirror edit in duplicate root [tests/test_agents.py](file:///d:/cyber-incident-tool/tests/test_agents.py#L2) line 2 — same change, to avoid drift between the two duplicated directories flagged in Stage 0.
**What's next**:
- Coverage currently 50% vs 70% required. Before Stage D, options are: (a) write the minimal suite of targeted tests that drive the 14 modules at 0%+poor coverage above 70%, or (b) relax the 70% rule until Stage G (your decision, PROJECT_RULES says ≥70%). Recommend (a) for Stage C+.
- Stage D per HANDOFF.md = run Scrapy spider(s) against real CERT-In / The Hacker News sites with rate-limited ≥2s delays. No scheduling gap work yet.
**Decision**: Coverage gap is NOTED. Real test suite (5/5 tests) runs clean with 1 import fix. Moving to Stage C bookkeeping and commit per instruction.

---

## Stage B — Database seed
**Date**: 2026-09-29
**What was verified and how**:
- Seed script location: **found 1 candidate only** — [backend/app/utils/seed.py](file:///d:/cyber-incident-tool/backend/app/utils/seed.py). No seed scripts in `ml/` (dataset_exporter, train_classifier, train_ner are unrelated), no `scripts/` directory exists.
- Seed script behaviour (from source read): defines `SEED_SECTORS` (13 rows: government, banking_finance, healthcare, energy_power, telecom, defence, transportation, education, it_ites, manufacturing, media, retail_ecommerce, other) + `SEED_SOURCES` (3 rows: CERT-In government_advisory, The Hacker News news_article, BleepingComputer news_article). **Deliberately inserts ZERO incidents.** Idempotent: does SELECT-then-skip-insert (per Sector.code / Source.name). Entrypoint: `if __name__ == "__main__": asyncio.run(seed_db())`.
- Invocation (against the live Stage A backend container): `docker exec cyber-incident-tool-backend-1 python -m app.utils.seed` → exit 0, final line `Database seeded successfully.` (full SQLAlchemy echo output captured, showing 13 sectors INSERTs + 3 sources INSERTs + 1 COMMIT).
- Direct DB row counts (psql UNION query against postgres container):
  | table | count |
  |---|---|
  | sectors | 13 |
  | sources | 3 |
  | incidents | 0 |
  | entities | 0 |
  All sample sectors 13 rows SELECTed match the code/name list exactly. All 3 sources (CERT-In, The Hacker News, BleepingComputer) show `is_active = t` and correct URLs/source_types.
- Idempotency re-run: second `python -m app.utils.seed` prints only SELECTs + COMMIT, no new INSERTs. Row count still sectors=13 / sources=3. Confirmed no double-seeding.
- API verification (curl from host):
  - `GET /api/v1/sources` → HTTP 200, 3 objects, each with correct `id,name,url,source_type,is_active,created_at,updated_at`. UUIDs in output match DB sample exactly. ✅
  - `GET /api/v1/incidents` → HTTP 200, `{"total":0,"page":1,"page_size":20,"incidents":[]}`. **Correctly still 0** — seed.py has no incident seed data. ✅ (This is expected per script source.)
  - `GET /api/v1/stats/overview` → HTTP 200, `total:0, by_sector:` lists all 13 sector names with 0 counts. Proves sectors and stats endpoint work end-to-end.
- ⚠️ **Plan-impacting note**: seed script intentionally contains NO incident sample rows. Therefore the `/api/v1/incidents` endpoint cannot be exercised with real incident payloads until either: (a) we hand-craft a small seed-incidents insert (your decision, I won't write it unprompted), or (b) Stage D (real scraping) produces the first rows. The API endpoint path IS proven to work (correct 200 JSON shape with 0 rows), but schema correctness for non-empty rows will need Stage D data or a deliberate seed-incidents script — your call.
**What changed**:
- No source code changes in Stage B (seed already present and worked first-shot).
- Database state changed: 13 sectors + 3 sources materialized in the docker-compose postgres volume (persists across `docker compose up/down`, survives as long as pgdata volume isn't `-v` wiped).
**What's next**:
- Your decision point first: do we (Option 1) hand-write a small 3–5 row sample incident seed so `/incidents` returns populated data before Stage D, OR (Option 2) go straight to Stage C pytest (we don't need incident rows for tests, which use SQLite in-memory + fixtures anyway), then do Stage D for real incident data? Recommended: Option 2 (proceed to Stage C tests now — Stage B goal was seed data, and seed was exactly what the shipped script provided; incident validation will come via Stage D).

---

## Stage A — Run the stack
**Date**: 2026-09-29
**What was verified and how**:
- `docker compose config` → parses OK (warns about obsolete version field only, harmless).
- `docker compose down -v ; docker compose up --build` (non-blocking, ~5 min build).
- 5 services listed in docker-compose.yml all come up. `docker ps`:
  | Name | Status | Ports |
  |---|---|---|
  | cyber-incident-tool-db-1 | Up 2m (healthy) | 5432 |
  | cyber-incident-tool-redis-1 | Up 2m | 6379 |
  | cyber-incident-tool-backend-1 | Up ~1m | 8000 |
  | cyber-incident-tool-agent_orchestrator-1 | Up ~1m | (no ports) |
  | cyber-incident-tool-dashboard-1 | Up ~1m | 8501 |
  No container marked `Restarting`.
- Service probes (curl from host):
  - `GET http://localhost:8000/health` → HTTP 200 `{"status":"healthy"}`
  - `GET http://localhost:8000/` → HTTP 200 `{"message":"Cyber Incident Intelligence API is running"}`
  - `GET http://localhost:8000/docs` → HTTP 200 (Swagger UI served)
  - `GET http://localhost:8000/openapi.json` → HTTP 200
  - `GET http://localhost:8000/api/v1/incidents` → HTTP 200 `{"total":0,"page":1,"page_size":20,"incidents":[]}` (valid JSON, empty is fine pre-seed)
  - `GET http://localhost:8501/_stcore/health` → HTTP 200 `ok` (Streamlit internal health check)
  - `GET http://localhost:8501/` → HTTP 200 (Streamlit HTML page)
- Migration applied cleanly: `docker logs backend` shows `alembic.runtime.migration Running upgrade -> 90218464f447, initial tables`; `docker exec db psql -c "\dt"` lists 7 tables (alembic_version, correlations, entities, incident_entities, incidents, sectors, sources) + no traceback.
- Orchestrator healthy: `docker logs agent_orchestrator` shows `Starting orchestrator queue consumer...` with `WARNING Spacy not installed` (graceful fallback — expected, intentional removal of spacy to fix the build), no ERROR/crash, no restart.
- **Services in docker-compose.yml, and the scraper/scheduler gap**: 5 services are defined: `db`, `redis`, `backend`, `agent_orchestrator`, `dashboard`. ⚠️ **There is NO `scraper` service and NO `scheduler` / cron service defined.** A `scraper/Dockerfile` exists (standalone image, CMD `scrapy crawl news`), but it is never referenced by docker-compose.yml. `SCRAPER_INTERVAL_MINUTES` in .env.example is referenced by no code/service. `agent_orchestrator` BLPOPs on `incident:raw` Redis queue but there is no producer. Result: the orchestrator idles forever on an empty queue. Scheduling gap is confirmed but out of scope for Stage A per instruction.
**What changed**:
- [backend/Dockerfile](file:///d:/cyber-incident-tool/backend/Dockerfile): Deleted the `RUN python -m spacy download en_core_web_sm` line because `spacy` package is not in [backend/requirements.txt](file:///d:/cyber-incident-tool/backend/requirements.txt) so pip would try to download non-existent module → build would fail. InsightAgent has a graceful ImportError fallback anyway, so NER degrades to regex only.
- No other code edits were needed to reach Stage A success.
**What's next**:
- Stage B: Database. Run seed script on empty DB; confirm alembic seed data present via /sources & /incidents API calls. Then Stage C: pytest.

---

## Stage 0 — Freeze and inspect pasted state
**Date**: 2026-09-29
**What was verified and how**:
- `git log --oneline -10` → 2 commits ("first commit", "second commit"); no prior verification commits exist.
- `git status` → HANDOFF.md locally modified (v3 update), nothing else uncommitted. No `.env` leakage.
- `python -m compileall backend scraper dashboard ml tests -q` → exit 0, zero output. No syntax errors anywhere. Paste damage at grammar level ruled out.
- `git ls-files` vs PROJECT_RULES.md structure → manually line-by-line compared.
- `__init__.py` presence manually verified in all backend/app/* and scraper/* package dirs via LS — all present.
**What changed**:
- Created this file (STATUS.md).
- Audit findings documented: 5 missing files, 1 double-nested package (scraper/scraper/), 1 duplicated tests/ folder (root + backend/tests), 3 extra tracked files (.coverage, dump.rdb, visualization_agent.py), 2 ML files not in training/ subdir, 1 dashboard page misnamed.
- No source files modified yet.
**What's next**:
- Apply Stage 0 blocker fixes (missing utils, scraper nesting, garbage files) → then Stage A: `docker-compose up --build`, verify all containers up and `/docs` returns 200.
