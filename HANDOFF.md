# HANDOFF.md (v3) — Indian Cyber Incident Intelligence Platform

> Repo-root file. Replaces earlier handoffs. This version assumes **no coding agent has access to your files**: the human runs every command and pastes files and outputs into a normal chat. That changes how the work must be done (see section 4).

---

## 1. Where things stand

**Project:** scrapes CERT-In and The Hacker News, filters incidents for India-relevance, classifies and deduplicates them through custom agents, stores them in PostgreSQL, serves them via FastAPI and a Streamlit dashboard. Built for SIH Problem ID 1677 (NTRO). Spec: `Synopsis_CyberIncidentTool.md`.

**History:**
1. Session 1 (AI) wrote all 9 phases and marked everything DONE on 2026-09-24 without running anything.
2. Session 2 (AI) started an audit and ran out of quota.
3. Gemini Code Assist in VS Code did not work.
4. Updated code was then obtained elsewhere and **pasted by hand into the intended files.** Nobody has yet verified that the pasted files landed correctly or that the project runs.

**Treat as unknown:** what the pasted code contains, whether any file is missing or misplaced, and whether anything runs. `PROGRESS.md` is a claim, not evidence. Only a command that ran successfully counts as proof.

---

## 2. Step 0 — Freeze and inspect the pasted state (do this before anything else)

Run in the project root (PowerShell or terminal):

```bash
git status --short
git diff --stat
git ls-files
```

1. **Commit the pasted state as a checkpoint** so nothing is lost and you can undo later mistakes:
   ```bash
   git add -A
   git commit -m "checkpoint: manually pasted updated code, unverified"
   git push origin main
   ```
   Before `git add -A`, confirm `.env` is listed in `.gitignore` and does not appear in `git status` output. Never push real secrets.
2. **Syntax check every Python file** (catches bad paste, broken indentation, truncated files):
   ```bash
   python -m compileall backend scraper dashboard ml tests -q
   ```
   Any output means a file has a syntax error. Note the file names.
3. **Compare against the expected structure.** The layout the project rules call for is: `backend/app/{api,agents,models,schemas,services,utils}`, `backend/alembic`, `scraper/{spiders,pipelines}`, `dashboard/{app.py,pages}`, `ml/`, `tests/`, plus `docker-compose.yml`, `.env.example`. Compare with the `git ls-files` output and list anything missing, misplaced (for example a file pasted into the wrong folder), or duplicated.
4. **Check `__init__.py` files** exist in every package folder under `backend/app/` and `scraper/`. Missing ones cause import errors that look mysterious.

Write down the results. They are the first entry in `STATUS.md`.

---

## 3. Definition of done

- [ ] `docker-compose up --build` starts every service with no crash loops
- [ ] Alembic migrations apply cleanly on an empty database; seed script runs
- [ ] `/docs` loads and `GET /api/v1/incidents` returns valid JSON
- [ ] At least one spider runs against the live site and yields real items
- [ ] Items flow Redis → orchestrator → PostgreSQL → API
- [ ] Non-India items are filtered out; relevant ones get attack type, severity, sector
- [ ] Duplicate reports are grouped, not stored twice
- [ ] Dashboard shows real stored incidents with working filters
- [ ] Scraping runs on a schedule without manual commands
- [ ] `pytest` passes, coverage reported honestly
- [ ] README and `PROGRESS.md` match what actually runs

Optional stretch: train the DistilBERT classifier and NER model. The rule-based classifiers are the working MVP.

---

## 4. The manual workflow (how work gets done now)

Because the AI cannot see your files or run commands, every fix follows this loop:

```
YOU run a command  →  copy the FULL output  →  paste into chat together with the
relevant file(s)  →  AI returns fixed code  →  YOU paste it into the file  →
run the command again  →  repeat until it passes  →  git commit
```

Rules that make this reliable:

- **AI must return complete file contents** for any file under about 150 lines, in one code block labeled with the exact path. For longer files it must give exact find-and-replace blocks ("find this text, replace with this") with the path. No "rest of the code unchanged" placeholders, and no partial snippets you would have to merge by hand.
- **One file per code block, path on top.** Paste into that path only.
- **Always paste real output**, complete, not a description of it. Include the command that produced it.
- **Always paste the file being fixed**, as it exists on disk now, not from memory of an earlier chat.
- **After every pasted change**, re-run `python -m compileall` on the folder before running the app. It catches paste damage in seconds.
- **Commit after each working step** (`git commit -am "stage B: migrations apply"`). A commit is your undo button.
- **If a chat gets long and the AI starts contradicting itself**, commit, start a fresh chat, and use the Resume prompt in `FIRST_PROMPT.md`.

Tool options: any chat assistant works for this loop (the Gemini web app, Claude, ChatGPT). Optionally try **Gemini CLI** in a terminal. It can read files and run commands itself, which removes the copy-paste loop. Check its current install steps and free-tier limits before relying on it. Your Gemini Plus subscription applies to the Gemini app, so confirm what it does and does not cover for the CLI.

---

## 5. Suspected problem areas (hypotheses to verify, not facts)

1. **Nothing may trigger the scrapers.** Docker Compose is documented as db, redis, backend, orchestrator, dashboard, with no scraper or scheduler. The orchestrator would wait on an empty queue. `SCRAPER_INTERVAL_MINUTES` may be unused.
2. **Migrations never applied.** Check that Alembic has actual version files, and whether the app also creates tables via `init_db()`. Use one approach, consistently (Alembic, per the project rules).
3. **Driver mismatch.** README mentions `psycopg`; dependencies list `asyncpg` and `psycopg2-binary`. The DB URL scheme must match an installed async driver.
4. **Stale spider selectors.** Written without testing against the live sites. Consider The Hacker News RSS feed if HTML parsing is fragile.
5. **Relevance filter too strict.** Global news may be almost entirely rejected by India-keyword rules. Test on real items.
6. **Tests may need live DB or Redis.** Decide whether to mock or start them.
7. **`tests/evaluate.py` is a placeholder.** Don't claim measured accuracy from it.
8. **Playwright may be unused.** Remove it if so.
9. **Paste damage (new).** Truncated files, wrong folders, tabs vs spaces, missing `__init__.py`, smart quotes from chat apps replacing straight quotes. `compileall` catches most of it.

---

## 6. Work plan

| Stage | Goal | Proof required |
|---|---|---|
| 0 | Freeze and inspect pasted state | Checkpoint commit; `compileall` clean; file list reviewed |
| A | Run the stack | All containers up; `/docs` loads |
| B | Database | Migrations apply to an empty DB; seed runs |
| C | Tests | `pytest` summary pasted; failures fixed |
| D | Scraping | Sample of real scraped items pasted |
| E | Pipeline | Item traced from Redis to `/api/v1/incidents` |
| F | Scheduling | Two automatic runs shown |
| G | Dashboard | Real data visible and filterable |
| H | Documentation | Docs match reality; checklist walked |
| I | ML (optional) | Labeled data, trained model, honest evaluation |

Log each finished stage in `STATUS.md` (date, what was verified and how, what changed, what's next). The AI writes the entry; you paste it into the file.

---

## 7. Ground rules (from PROJECT_RULES.md, still binding)

- One tool per job. No MongoDB, Kafka, React, LangChain, CrewAI, AutoGen, or paid APIs. No local LLMs for MVP classification.
- Respect `robots.txt`; at least 2 seconds between requests to one site; no CAPTCHA bypass; no paywalled or login-gated content; no dark web.
- Attribute every incident to its source. Store no personal data.
- Schema changes only through Alembic.
- PEP 8, type hints, Google-style docstrings.
- Never mark anything DONE without a command that proved it.
- Never commit `.env` or real secrets.

---

## 8. Realistic expectations

Achievable: a working, demoable India-focused incident feed with a real API and dashboard, suitable for a hackathon or portfolio. Not achievable without much more work: something CERT-In or a SOC could rely on. That needs more sources, monitoring, human review of classifications, and evaluation on labeled data.
