# Horizon

> 🏗️ **Under construction — v2 rebuild in progress.** This branch contains the
> project design and empty Rust library foundations. There is no runnable desktop
> app or CLI yet.

Horizon is being built as a free, open-source, local-first decision workstation to
help people understand their options, inspect the evidence and assumptions behind
them, compare adaptive plans, and revise those plans from experience.

The planned core has two independent libraries:

- **hsim** will model actions, limited resources, uncertainty, and alternative policies.
- **hdb** will store evidence and observations, retrieve relevant context, and provide
  replaceable access to BYOK and local models.

The planned desktop and CLI applications will compose these libraries. Essential
workflows must work without a model, an account, a paid API, or a cloud service.

## Current state

`main` contains the v2 architecture, build plan, contributor rules, and a minimal
buildable Rust workspace. The libraries have no runtime APIs yet. Simulation,
database operations, model adapters, and the desktop application are planned,
not implemented. Do not interpret the scaffolding as a working product.

The next milestone is **M1: contracts and a deterministic simulation slice**,
including a synthetic case and a minimal CLI demonstration. See the
[build plan](docs/BUILD_PLAN.md) for acceptance gates; later milestones remain pending.

The previous Python/React workstation and the complete `lifesim` snapshot are
preserved on [`old`](https://github.com/kanishkpaul/horizon/tree/old), with a new
README and historical audit. Legacy behavior is reference material, not an
acceptance oracle. New development belongs on `main`.

## Planned stack

| Responsibility | Choice |
|---|---|
| Libraries and application services | Rust |
| Desktop delivery | Tauri 2 |
| Interface | TypeScript, React, Vite |
| Authoritative records | SQLite |
| Semantic retrieval | Embedded vector adapter; benchmark LanceDB OSS and sqlite-vec |
| Model access | Native provider adapters and a configurable compatible endpoint |
| Numerical parallelism | Bounded Rayon workers when justified by measurement |
| Advanced scheduling | Optional OR-Tools worker |
| Research interface | Optional Python bindings to the same engine |

The vector backend and embedding model are deliberately not selected yet. They
must meet the same correctness, filtering, retrieval, footprint, and recovery
checks. A vector index is derived data; source evidence remains authoritative.

## Start contributing

Read [AGENTS.md](AGENTS.md), [the architecture](docs/ARCHITECTURE.md),
[the build plan](docs/BUILD_PLAN.md), and [the coding standard](docs/CODE_STYLE.md).

To check the foundation, use Rust 1.85 or newer with edition 2024 support and
Python 3.11 or newer:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo doc --workspace --no-deps
python3 scripts/check_repository.py
```

These currently verify the foundation only. They do not exercise a simulation or
database implementation. Cargo is needed for the Rust workspace; Python is used
only by the repository check. End users will not need Python for core functionality.

## Documents

- [Project scope](docs/PROJECT.md)
- [Build plan](docs/BUILD_PLAN.md) and [decision record](docs/DECISIONS.md)
- [Architecture](docs/ARCHITECTURE.md) and [feature lifecycle](docs/FEATURES.md)
- [hsim contract](docs/HSIM.md) and [hdb contract](docs/HDB.md)
- [Model access and privacy](docs/MODELS.md)
- [Validation and performance](docs/VALIDATION.md)
- [Legacy preservation and migration](docs/MIGRATION.md)
- [Coding and commenting standard](docs/CODE_STYLE.md)
- [Contributing](CONTRIBUTING.md) and [security](SECURITY.md)

## Ownership and license

Users own their workspaces and choose which context, if any, leaves their device.
API keys belong in the operating system's credential store, never in a database,
export, or repository. Local mode never falls back to a cloud provider silently.

Source code is licensed under [MIT](LICENSE). Private records and third-party
materials do not become redistributable because the software is open source. The
repository is public; release contents are still reviewed before each release.

Horizon is decision support under explicit assumptions. It does not establish
personal outcome probabilities or predict a person's life.
