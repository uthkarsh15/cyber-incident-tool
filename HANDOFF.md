# HANDOFF.md — Reading This First

> You're picking up the **Indian Cyber Incident Intelligence Platform** (`cyber-incident-tool`) from a teammate who ran out of AI tokens partway through. This file tells you what's real, what's not, and what to do next.

---

## 1. What this project is

An automated pipeline that scrapes CERT-In and The Hacker News for cybersecurity incidents, filters/classifies them for India-relevance via a custom agent pipeline, stores them in Postgres, and serves them through a FastAPI backend + Streamlit dashboard.

Full spec lives in `Synopsis_CyberIncidentTool.md` (SIH Problem ID 1677, NTRO).

---

## 2. Read the docs in this order

The repo already has a full internal doc system — **don't skip it, and don't let an AI assistant skip it either**:

1. **`PROJECT_RULES.md`** — the master rulebook. Tech stack (exact versions, what's explicitly banned — no MongoDB, no Kafka, no LangChain, no paid APIs), folder structure, coding standards, env vars, git conventions, ethical scraping rules. Read this before writing a single line.
2. **`ARCHITECTURE.md`** — system design / component diagram.
3. **`DATA_MODELS.md`** — DB schema, Pydantic models, API contracts.
4. **`AGENT_DESIGN.md`** — spec for the 5-agent pipeline (relevance → classification → correlation → insight → orchestrator).
5. **`IMPLEMENTATION_PLAN.md`** — the original phase-by-phase build order.
6. **`PROGRESS.md`** — the living tracker. **Read this last and skeptically** (see below).

---

## 3. The important caveat: "DONE" ≠ "verified working"

`PROGRESS.md` shows all 9 phases as ✅ DONE. Don't take that at face value. The **Known Issues & Blockers** table in that same file, and notes buried in individual task rows, tell the real story:

| What the tracker says | What it actually means |
|---|---|
| Phase 1–9 all ✅ DONE | Code exists for every planned file. It has **not** been run end-to-end. |
| "Alembic Setup — ✅ DONE" | Note says *"migrations fail to apply (DB not running locally)"* — never actually tested against a real Postgres instance. |
| "ML Models — ✅ DONE" (Phases 8.1–8.4) | This is **scaffolding only**. No labeled training data exists yet, so the DistilBERT classifier and NER model have never actually been trained. |
| "CERT-In website may change structure" (Medium, Open) | Spider selectors were written against the site's HTML at one point in time — untested for whether they still match. |
| "No labeled training data yet" (Medium, Open) | Blocks real ML work until someone curates a dataset. |

**Translation: treat this as a project where every file has a first draft, but nothing has been proven to actually run.** Your first job isn't writing new features — it's verification.

---

## 4. Environment setup

### Option A — Docker (recommended, matches `README.md`)
```bash
git clone https://github.com/uthkarsh15/cyber-incident-tool
cd cyber-incident-tool
docker-compose up --build
```
- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs

### Option B — Local (no Docker)
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r backend/requirements.txt
```
Then install PostgreSQL + Redis locally, copy `.env.example` → `.env` and fill in values, and follow the run commands in `PROJECT_RULES.md` §10 (migrations → FastAPI → orchestrator → Streamlit, each in its own terminal).

Full dependency list (backend, scraper, ML, dashboard, spaCy model) is at the bottom of `PROGRESS.md`.

---

## 5. What to actually do first (in order)

1. **Get it running.** Either Docker or local. This alone will surface most of what's broken — expect migration errors, missing packages, and spider selector mismatches.
2. **Run the test suite**: `cd backend && pytest -v --tb=short`. `PROJECT_RULES.md` requires 70% coverage per phase — check if that's real or aspirational.
3. **Run one spider manually** against CERT-In / The Hacker News and confirm items actually make it into Redis → Postgres via the orchestrator. This is the piece most likely to be silently broken (site structure drift).
4. **Once the pipeline runs end-to-end on real data**, update `PROGRESS.md` with what you found — that's the project's own convention (see §9 of `PROJECT_RULES.md`, "Documentation Update Protocol"). Every completed task should get a status, date, and notes; every changed schema/agent/architecture piece should update the matching doc.
5. **Only then** move on to real remaining work: curating a labeled dataset and actually training the ML models (Phase 8 is the one phase that's genuinely not just "unverified" but not-yet-startable without data).

---

## 6. Ground rules to keep following

From `PROJECT_RULES.md` — these are binding, not suggestions:
- Exactly one tool per job — don't swap in MongoDB, Kafka, React, LangChain, etc.
- No paid APIs, ever.
- Respect `robots.txt`, minimum 2-second delay between scraper requests, no CAPTCHA bypassing, no dark-web crawling, no PII storage.
- Alembic only for schema changes — never touch the DB directly.
- Update `PROGRESS.md`, and any other doc affected, after every task.

---

## 7. Handing this to an AI assistant

See the prompt below — give it to Claude (or whichever assistant you're using) as your opening message in a fresh conversation, with the repo cloned and accessible (or key files pasted in if it can't browse your local files).
