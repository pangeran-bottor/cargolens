# Development Work Log

Reconstructed from git history (commit times = phase completions) plus session
notes. Wall-clock windows include breaks; **active** is the honest estimate of
hands-on time.

This log exists for two reasons: **transparency toward the reviewer** (honest
effort accounting against the stated 6–10h expectation, alongside the AI-usage
disclosure in the README) and **a self-audit** — keeping per-phase time and
verification records makes it visible where the process was efficient (the
deploy dry run) and where the budget actually went.

## Timeline

### Day 0 — Planning
| Activity | Active est. |
|---|---|
| Spec & dataset analysis, architecture plan, data-correctness decisions | ~1.0h |

### Day 1 — Prep + main build
| Done at | Milestone | Window | Active est. |
|---|---|---|---|
| ~12:00 | Plan review: independently re-verified every dataset statistic against the CSV; added hardening items (rate limiting, LLM-failure path) | morning | 0.5h |
| ~13:00 | Deployment dry run: throwaway two-service app on Railway to de-risk the real deploy (caught 3 gotchas in advance) | midday | 0.75h |
| 15:10 | **Phase 0** — repo scaffold, CSV→SQLite seed with correctness rules baked in, seed counts verified | ~14:25–15:10 | 0.75h |
| 15:58 | **Phase 1** — deterministic query engine (validated specs → parameterized SQL), 5 KPIs, 7 tests with independently recomputed expectations | 15:10–15:58 | 0.8h |
| 19:07 | **Phase 2** — dashboard UI (KPI cards + 3 charts), verified via headless-browser screenshot | 15:58–19:07 *(incl. ~2h break)* | 1.0h |
| 21:03 | **Phase 3** — LLM orchestration (tool-calling → validated specs), dataset-anchored date resolution, rate limiting, 4 live tests against engine ground truth | 19:07–21:03 | 1.3h |
| 21:57 | **Phase 4** — chat panel, dynamic chart rendering, "how this was computed" explainability panel | 21:03–21:57 | 0.9h |
| 22:39 | **Phase 5** — forecasting tool (moving average + linear trend), SKU→category roll-up, inventory recommendation, 6 tests | 21:57–22:39 | 0.7h |

### Day 2 — Deploy + finish
| Done at | Milestone | Window | Active est. |
|---|---|---|---|
| 10:20 | **Phase 6** — Railway deploy (both services), CORS + end-to-end verified live; Node-version build failure diagnosed and fixed | ~09:45–10:20 | 0.6h |
| 10:22 | **Phase 7** — full README, AI-usage disclosure, secret scan, GitHub push | alongside P6 | 0.3h |
| 11:20 | Reviewer access-code gate (backend middleware + unlock UI), deployed and verified | 10:25–11:20 | 0.7h |
| 11:29 | Final polish — `CLAUDE.md` (AI-collaboration guidance + vendored karpathy-guidelines skill) and this work log | 11:20–11:30 | 0.3h |
| 12:28 | Review-pass improvements: documented concrete chat limits; persistent example questions covering all 3 intelligence levels; Markdown rendering for answers; future-improvements rewrite (observability, semantic layer) | 11:40–12:30 | 0.8h |

## Totals

| Bucket | Hours |
|---|---|
| Build (Phases 0–7 + access gate + polish) | **~8.2h** |
| Build-day prep (plan review + deploy dry run) | ~1.25h |
| **Total** | **~9.5h** (+ ~1h planning on day 0) |

Inside the 6–10h expectation. The deploy dry run paid for itself:
the production deploy took ~35 minutes because its three failure modes had
already been hit and documented in the throwaway project.

## Process notes

- Sequencing: the deterministic engine was proven (tests + dashboard) **before**
  the LLM was wired to it, so the AI layer routed to an engine already known
  correct — and there was a working, demoable product at every point after hour 3.
- Every phase ended with a verification step: pytest suites whose expected
  values are recomputed independently from the raw CSV, live LLM tests asserted
  against engine ground truth, and headless-browser screenshots of both local
  and production builds.
- Built with AI assistance (Claude Code) under human direction, following the
  vendored [karpathy-guidelines](.claude/skills/karpathy-guidelines/SKILL.md)
  working style — see `CLAUDE.md`. Disclosed in the README.
