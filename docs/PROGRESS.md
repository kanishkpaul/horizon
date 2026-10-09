# Progress (2026-10-09, session 1 — stopped at usage limit)

## Done and verified
- Persistent project, git, read-only raw inputs with SHA256SUMS (`data/raw/`, gitignored).
- SQLite knowledge store with migrations: temporal claims (valid/recorded/source/access time, supersession), sources, orgs, people, events, hypotheses, outreach targets, parameters with history, strategies, objectives, runs, actions, outcomes, forecasts, media, revisions (undo).
- Importer: 501 radar opportunities (all 163 fields preserved), 3,392 claims, 657 sources, 83 outreach targets, 104 events. Deadline normalization with precision labels.
- Research workers: verification (75 claims, 11 workbook claims superseded, 17 new opps), discovery (52 opps, 18 creation hypotheses), base rates (80 evidence records). Summaries in `research/agents/*/summary.md`.
- Rule-based eligibility engine with reasons; hybrid search (FTS5 BM25 + bge-small embeddings + RRF).
- Simulation engine (vectorized, CRN, latent factors, exogenous hazards, resolve-time probabilities, adaptive rules), 40 actions, 67 parameters with origins, 10 preset strategies, 8 value models.
- Analysis: ranking with risk measures + hard constraints, paired dominance, Pareto, EVPPI with noise floor, Spearman sensitivity, convergence, scenario regret, tornado, NSGA-II strategy search, execution plan generation, power-prior Beta calibration, forecast scoring.
- 18 validation tests passing (`uv run pytest` in backend/). CLI: `uv run horizon rebuild|simulate|serve|reseed`.
- FastAPI app (`backend/horizon/api.py`).
- Frontend (frontend/src): styles/tokens, shell, horizon ruler, command palette, inspector, charts, Brief, Atlas, Graph, Lab, Theater, TheaterFrame, RenderFrame.

## Not done (next session, in order)
1. Frontend views still missing so the build does not compile yet: `views/Cockpit.tsx`, `views/ModelView.tsx`, `views/Research.tsx`. Then `npm run build` and fix type errors.
2. Backend `horizon/media.py` (`start_render`): build spec via `theater.build_spec`, store media row, run `frontend/scripts/render.mjs` (playwright-core + cached chromium_headless_shell-1234 executablePath, `window.__horizonSetT`, PNG frames → ffmpeg MP4, WebVTT captions, optional `say` narration).
3. `horizon/search_eval.py` QRELS and retrieval benchmark.
4. End-to-end verification in the browser; docs (PROJECT.md, CLAUDE.md, METHODOLOGY_REGISTRY.md, ASSUMPTIONS.md, MODEL_CARD.md, VALIDATION.md, DECISIONS.md, AUDIT.md, RESEARCH_LEDGER.md); adversarial review; recommendations.
