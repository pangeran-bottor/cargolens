# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this is

CargoLens: an AI-powered logistics analytics dashboard. FastAPI backend
(`backend/`) + Next.js 16 frontend (`frontend/`), deployed as two Railway
services. Full product/architecture context is in `README.md` — read it first.

## Commands

```bash
# backend (from backend/)
.venv/bin/uvicorn app.main:app --reload --port 8000   # run (auto-seeds SQLite)
.venv/bin/python -m pytest tests/ -q                  # 17 tests; 4 live LLM
                                                      # tests skip w/o ANTHROPIC_API_KEY

# frontend (from frontend/)
npm run dev      # http://localhost:3000
npm run build    # must pass before any frontend commit
```

## Architecture invariants — do not violate

1. **The LLM never computes numbers and never writes SQL.** It only selects a
   tool and emits a typed spec (`QuerySpec` / `ForecastSpec`). All arithmetic
   happens in `backend/app/queries.py` / `forecast.py`, compiled to
   parameterized SQL from allow-listed fragments. If you add a capability,
   extend the spec + engine — never let model output reach the database.
2. **One computation path.** Dashboard endpoints and AI tools call the same
   `run_query(spec)`. Don't add a second way to compute a metric.
3. **Relative dates anchor to the dataset's max order_date (2025-12-30)**, not
   the wall clock. The data is a fixed historical year.
4. **Data-correctness rules are deliberate** (documented in README
   "Assumptions"): on-time rate over completed orders only; avg delivery time
   excludes the 30 rows without delivery_date; demand = sum(quantity);
   forecasts at category level, never per-SKU. Don't "fix" these without
   reading the rationale.
5. **The database is read-only at query time** and rebuilt from
   `backend/data/mock_logistics_data.csv` on startup. Never mutate it.

## Testing convention

Expected values in tests are **recomputed independently from the raw CSV with
stdlib code** — never derived from the engine under test. Keep it that way: a
shared bug must not be able to make a wrong number pass. Live LLM tests assert
against engine ground truth, not against memorized strings.

## Deploy notes

Railway, two services, CLI-linked per subdirectory (`railway link` inside
`backend/` / `frontend/`). Gotchas already paid for: set `NEXT_PUBLIC_*` vars
before the first build (build-time inlining); nixpacks needs
`"engines": {"node": ">=22"}` or it builds Next 16 on Node 18; Railway blocks
deploys of dependencies with known CVEs — pin current patch versions.

## Working style — LLM-efficiency guidelines

This repo vendors the [karpathy-guidelines](.claude/skills/karpathy-guidelines/SKILL.md)
skill (MIT), used throughout development to keep LLM-assisted coding efficient
and disciplined. Claude Code auto-loads it here. Its four rules, as they apply
to this repo:

1. **Think before coding** — surface assumptions explicitly. Here that means:
   data-correctness decisions go in README "Assumptions", not silently into code.
2. **Simplicity first** — this is a take-home with an explicit "do NOT
   over-engineer" instruction. No speculative abstractions; the cut-list
   mentality applies (smallest change that satisfies the requirement).
3. **Surgical changes** — match existing style; every changed line traces to
   the request. Don't refactor adjacent code opportunistically.
4. **Goal-driven execution** — every phase ends with a verification step
   (tests with independent expectations, live e2e checks, headless-browser
   screenshots). Don't claim done without running the check.

## Boundaries

- Never commit secrets. `ACCESS_CODE` and `ANTHROPIC_API_KEY` live only in
  Railway env vars / local shells. `.env*` is gitignored (except `.env.example`).
- This repo is public — keep employer-specific context out of it.
