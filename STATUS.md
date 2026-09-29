# STATUS.md — Stage-by-Stage Verification Log

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
