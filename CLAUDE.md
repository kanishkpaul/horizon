# Working on Project Horizon

This is the preserved `old` branch. New development belongs on `main`. Follow
`AGENTS.md` and `README.md` first. Never add coding-agent co-author trailers,
generated-by signatures, or coding-agent attribution to commits, pull requests,
documentation, or source. Preserve third-party license notices.

Read `PROJECT.md` first, then `docs/PROGRESS.md` for the current state.

## Rules
- Originals in `data/raw/` are read-only. Never overwrite them; re-import with `uv run horizon rebuild`.
- Facts go in as **claims** with a source, grade, method and dates. New evidence supersedes old claims; never delete history.
- Every simulator parameter needs an honest `origin`. Use `published_empirical` only when the population matches this person; otherwise use `expert_judgment` and cite the nearest evidence. Placeholders stay `illustrative_placeholder`.
- Never present a created-opportunity hypothesis as a vacancy (`access_class`).
- Do not send messages, submit applications, or contact anyone. Draft only.
- After changing `data/seed/*.yaml`, run `uv run horizon reseed` (keeps profile edits) and `uv run pytest -q`.
- After frontend changes: `cd frontend && npx tsc --noEmit && npm run build`, then restart `uv run horizon serve`.
- Verify UI changes in a browser (gstack `/browse`) and look at screenshots; for video changes, extract frames with ffmpeg and look at them.
- Copy the database with SQLite's backup API or `VACUUM INTO` (WAL mode), never `cp`.

## Layout
`backend/horizon/` — `db.py` (schema and migrations), `ingest.py`, `research_ingest.py`, `eligibility.py`, `search.py`, `service.py`, `api.py`, `sim/` (params, conditions, model, engine, analysis), `strategy_search.py`, `analysis_jobs.py`, `execution.py`, `theater.py`, `media.py`, `cli.py`.
`frontend/src/` — `views/` (one per workspace), `components/` (charts, `TheaterFrame`, inspector, palette, horizon ruler), `lib/`.
`data/seed/` — profile, parameters, actions, strategies, objectives (the model's editable source).
`research/` — worker outputs, experiments, profile brief.
