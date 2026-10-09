# Project Horizon

A local decision workstation for one person's next 12 months: what opportunities exist, which could be created, what to do first, and how much each conclusion depends on assumptions you can change.

It is decision support. It compares adaptive policies under explicit, sourced, editable assumptions. It does not predict your life.

## Run it

```bash
cd backend && uv sync && uv run horizon serve      # http://127.0.0.1:8765
```

The database (`data/horizon.sqlite3`) is already built. To rebuild from the original workbooks and research outputs:

```bash
cd backend && uv run horizon rebuild               # import → research ingest → index → eligibility (~40 s)
cd frontend && npm install && npm run build        # only after frontend changes
```

Other commands: `uv run horizon simulate --objective robust --worlds 4000`, `uv run horizon eval-search`, `uv run horizon reseed` (reloads parameters, value models and preset strategies from `data/seed/`), `uv run pytest -q`, `uv run python scripts/experiments.py`.

## Workspaces
| Key | Workspace | Answers |
|---|---|---|
| 1 | Brief | What ranks first under my values, what is due now, which questions to answer first |
| 2 | Atlas | Every opportunity, with eligibility reasons and graded evidence; add any to the model |
| 3 | Graph | Relationships, and the unlock map (which actions enable or strengthen which) |
| 4 | Scenario lab | Re-simulate with different hours, AI speed-up, what-ifs and value models; tradeoffs, dominance, value of information, robustness, tornado, strategy search, full run record |
| 5 | Theater | Replay one simulated world event by event; render an explainer MP4 of that exact world |
| 6 | Cockpit | Dated action plan from a strategy; log outcomes that recalibrate parameters; forecasts with Brier scores |
| 7 | Model & values | Profile, value models, parameter registry, action catalogue, strategies |
| 8 | Research | Ledger, evidence and superseded claims, creation hypotheses, outreach targets, events, gaps, method docs |

`⌘K` searches everything (hybrid BM25 + local embeddings). Undo is in the rail.

## Architecture
```
data/raw (read-only originals + SHA256SUMS)
   │ ingest.py            normalise; every field kept in raw_json; claims graded by the sheet's own labels
   ▼
SQLite (data/horizon.sqlite3) ── claims (temporal, superseding) · opportunities · orgs · people · events
   ▲ research_ingest.py   hypotheses · parameters · strategies · value models · runs · actions · outcomes · media
   │                      FTS5 + embeddings (search.py) · eligibility.py (rules vs editable profile)
research/agents/*.jsonl
   ▼
sim/ (model.py → engine.py → analysis.py)   vectorised Monte Carlo over an AND/OR action graph, CRN, EVPPI, Pareto, regret
strategy_search.py (NSGA-II) · analysis_jobs.py (regret, tornado) · execution.py (plans, calibration) · theater.py · media.py
   ▼
api.py (FastAPI) ──► frontend/ (React + d3 + Cytoscape) ──► scripts/render.mjs (headless Chromium frames → ffmpeg MP4)
```

## Documents
- [docs/AUDIT.md](docs/AUDIT.md): what the original sheets contain, and their errors.
- [docs/RECOMMENDATIONS.md](docs/RECOMMENDATIONS.md): strategy experiments and the immediate plan.
- [docs/METHODOLOGY_REGISTRY.md](docs/METHODOLOGY_REGISTRY.md): methods considered, used and rejected.
- [docs/MODEL_CARD.md](docs/MODEL_CARD.md), [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md), [docs/VALIDATION.md](docs/VALIDATION.md), [docs/ADVERSARIAL_REVIEW.md](docs/ADVERSARIAL_REVIEW.md).
- [docs/DECISIONS.md](docs/DECISIONS.md), [docs/RESEARCH_LEDGER.md](docs/RESEARCH_LEDGER.md), [docs/PROGRESS.md](docs/PROGRESS.md).

## Privacy
Everything runs locally. The repository holds personal data (profile seed, outreach targets with public emails). Keep it private if you ever push it. Nothing in this project sends messages or applications.
