# Horizon — legacy implementation

This is the preserved Python/React implementation of Horizon. New development takes
place on [`main`](https://github.com/kanishkpaul/horizon/tree/main), with two Rust
components: `hsim` for simulation and `hdb` for evidence, storage, retrieval, and
model access. This branch is named `old` and remains a reference and migration
source.

## What is preserved

- The local opportunity and decision workstation: Python, FastAPI, React,
  SQLite, BM25, local embeddings, simulation, analysis, scheduling, and playback.
- The complete `lifesim` import from commit `25c9f9a`.
- Declarative models, ingestion code, tests, research records, and project docs.
- The previously untracked audit in `docs/analysis-2026-10-10/`, including its
  reproduction script. It is historical evidence, not a certification of current
  opportunity deadlines or calibrated personal predictions.

The implementation is decision support under explicit assumptions. It does not
predict a person's life. The workstation and `lifesim` are separate engines.

## Running the workstation

Use Python 3.12 and `uv`. Build the interface with Node.js and npm:

```sh
cd frontend
npm ci
npm run build
cd ../backend
uv sync
uv run horizon serve
```

The local app is served at `http://127.0.0.1:8765`.

The original database and source workbooks are ignored by Git. A fresh clone does
not contain the complete personal workspace. Restore those files from a private
backup before running the populated workstation. Rebuilding also requires its
original inputs; `horizon rebuild` is not a synthetic-data initializer. Embedding
search requires the configured model to be available locally or downloaded.

See [PROJECT.md](PROJECT.md) for workspaces, commands, and architecture.

## Running lifesim

```sh
cd lifesim
python3 -m lifesim --domain all --u 0.3 --seed 1
python3 -m tests.run
```

Its simulation core uses the Python standard library. Plotting has optional
dependencies. Its coefficients and population reference curves are illustrative;
simulation precision does not validate them against real lives. See
[lifesim/README.md](lifesim/README.md).

## Known limitations and migration

The audit reproduced incorrect fractional-window capacity allocation, cutoff
semantics, risk comparisons, incomplete model fingerprints, disconnected profile
inputs, non-atomic outcome calibration, duplicated discovery edges, and plan
regeneration problems. Preserve these examples as regression cases for v2 rather
than copying the defects. Existing test passes do not remove these limitations.

See [the audit](docs/analysis-2026-10-10/REPORT.md) and
[the v2 build plan](https://github.com/kanishkpaul/horizon/blob/main/docs/BUILD_PLAN.md).
Changes to this branch should be limited to preservation, documented migration,
or explicitly requested maintenance.

## Private workspace preservation

Git preserves tracked files and history, not ignored databases, originals,
simulation archives, or rendered media. A consistent SQLite backup and copies of
the source originals, run arrays, media, and audit files were verified separately
before the branch split on 13 October 2026. Preserve those private backups outside
the repository. Use SQLite's backup API for databases in WAL mode.

The branch contains personal context in tracked models and research material.
The repository remains private; do not publish this history without a separate
privacy and licensing review. The v2 source is intended to be free and open source.

## Contribution rule

Use the contributor's configured Git identity. Do not add coding-agent co-author
trailers, generated-by signatures, or coding-agent attribution to commits, pull
requests, documentation, or source. Preserve legitimate third-party license
notices.
