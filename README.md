<div align="center">

<h1>Horizon</h1>

<h3>Understand possibilities. Make feasible commitments. Learn as the world changes.</h3>

<p>An open-source, local-first decision OS.<br />
Keep knowledge, possibility, commitment, and experience connected.</p>

<p>
  <a href="docs/THESIS.md">The thesis</a> ·
  <a href="docs/STATUS.md">Current status</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a> ·
  <a href="CONTRIBUTING.md">Contribute</a> ·
  <a href="LICENSE">MIT</a>
</p>

[![Foundation checks](https://github.com/kanishkpaul/horizon/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kanishkpaul/horizon/actions/workflows/ci.yml)

</div>

---

> **Under construction.** `main` contains design contracts, repository tooling,
> and two empty Rust library crates. There is no runnable decision engine,
> evidence store, CLI, or desktop app yet. The previous implementation is
> preserved on [`old`](https://github.com/kanishkpaul/horizon/tree/old).

## A decision should outlive the moment you make it

A choice connects what you know, what you value, what you expect, and what you
can actually do. New evidence arrives. Other people respond. Resources change.
The reasons behind a commitment should remain available when it is time to revise it.

Horizon is being built around a **living decision case**: evidence, assumptions,
alternatives, resources, policies, commitments, and observations held together
in a record you own.

| Ask | What a case should help you inspect |
| --- | --- |
| **What can I do?** | Feasible alternatives, prerequisites, resources, and deadlines |
| **What matters to this choice?** | Your priorities, supporting evidence, conflicts, and consequences for others |
| **What would change my mind?** | Decision thresholds, fragile assumptions, and changed sources |
| **What should I learn first?** | Consequential unknowns, information costs, and small experiments |
| **What remains possible afterward?** | Contingencies, switching costs, and options kept open |

These are product goals. [Current status](docs/STATUS.md) separates them from
implemented behavior.

## Two libraries. One continuous learning loop.

**Know → Explore → Commit → Observe → Revise**

**[`hdb`](hdb/)** provides the evolving account of reality. It will preserve
statements with their sources, temporal validity, applicability, conflicts,
and revision history. Structured queries, lexical search, dependency traversal,
and optional semantic retrieval will help find evidence a decision needs.
Embeddings remain replaceable views over preserved records.

**[`hsim`](hsim/)** explores what actions could produce. It will evaluate
adaptive policies under explicit resource limits, mechanisms, and uncertainty.
Social models will make other people's responses inspectable assumptions.
Every run consumes a frozen case; simulation never calls a model or network service.

**The application** connects the independent libraries. It will assemble reviewed
evidence into immutable cases, explain conditional comparisons, turn chosen
policies into feasible commitments, and bring actual outcomes back for review.
Simulation and execution must agree on deadlines, prerequisites, and resource use.

Read the [full thesis](docs/THESIS.md) and [architecture](docs/ARCHITECTURE.md).

## Built around human agency

- **Local ownership.** Portable records, inspectable revisions, backup, and recovery.
- **Useful without a model.** The essential loop must work offline without an
  account, API key, model download, or hosted service.
- **Optional intelligence.** Local models and your own provider keys can assist
  retrieval and propose changes. Acceptance remains explicit.
- **Honest uncertainty.** Evidence, assumptions, suggestions, observations, and
  simulated outcomes retain distinct meanings. Scenarios do not acquire invented probabilities.
- **Explicit priorities.** Natural units and visible tradeoffs, including effects
  on affected people. Users decide what matters.
- **Open infrastructure.** MIT-licensed libraries and public contracts that others
  can inspect, extend, and use in different domains.

Local mode must never silently fall back to a cloud provider. A simulation is
conditional on its model; it does not establish personal outcome probabilities.

## Inside the foundation

| Area | Direction | Status |
| --- | --- | --- |
| Simulation and evidence libraries | Independent Rust crates | Buildable shells; no runtime APIs |
| Authoritative records | SQLite and preserved source artifacts | Planned |
| Retrieval | Structured, lexical, dependency, optional vector search | Planned; vector backend undecided |
| Application services and CLI | Rust; shared case and execution semantics | Planned |
| Desktop workspace | Tauri 2, TypeScript, React, Vite | Planned |
| Optional capabilities | Model roles, solver worker, Python bindings, media | Planned; separate lifecycles |

The first domain is research and career planning. The first target is a small,
synthetic decision that can be compared, committed to, and reviewed without a model.

## Work on Horizon

Rust **1.85+** and Python **3.11+**. These commands check the existing foundation;
they do not run a decision workflow. Python is repository tooling, not a planned
end-user requirement.

```sh
git clone https://github.com/kanishkpaul/horizon.git
cd horizon
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
RUSTDOCFLAGS="-D warnings" cargo doc --locked --workspace --no-deps
python3 scripts/check_repository.py
python3 -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before editing.
The [current acceptance gate](docs/BUILD_PLAN.md) is public; detailed owner planning
stays local. No private planning file is required to contribute.

| Understand | Build and verify |
| --- | --- |
| [Thesis](docs/THESIS.md) · [Project scope](docs/PROJECT.md) | [Contributing](CONTRIBUTING.md) · [Coding standard](docs/CODE_STYLE.md) |
| [Status](docs/STATUS.md) · [Architecture](docs/ARCHITECTURE.md) | [hsim contract](docs/HSIM.md) · [hdb contract](docs/HDB.md) |
| [Decisions](docs/DECISIONS.md) · [Legacy preservation](docs/MIGRATION.md) | [Capability lifecycle](docs/FEATURES.md) · [Model permissions](docs/MODELS.md) |
| [Design direction](design/README.md) | [Validation](docs/VALIDATION.md) · [Security](SECURITY.md) |

---

<p align="center"><em>Greater agency through connected knowledge, possibility,
commitment, and experience—and tools that belong to everyone.</em></p>

Source code: [MIT](LICENSE). Private records and third-party materials retain
their own ownership and redistribution conditions.
