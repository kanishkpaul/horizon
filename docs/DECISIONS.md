# Decisions

13 October 2026. These records distinguish settled direction from implementation.

| ID | Decision | State | Reason |
|---|---|---|---|
| D-001 | Preserve old implementation on `old`; develop v2 on `main` | Applied | Retain code, history, and counterexamples while establishing coherent boundaries |
| D-002 | Two independent Rust libraries: hsim and hdb | Foundation applied | Simulation and evidence have separate contracts and lifecycles |
| D-003 | Tauri 2 with TypeScript/React/Vite | Planned | Native Rust composition with reusable web UI |
| D-004 | SQLite is authoritative; vector indexes are derived | Planned | Evidence and transactions need durable semantics independent of retrieval |
| D-005 | Benchmark LanceDB OSS and sqlite-vec through one adapter | Open selection | Rust compatibility, embedded deployment, filtering, relevance, and footprint must be measured |
| D-006 | BYOK, local, and no-model operation; independent model roles | Required, pending | User choice and offline core functionality |
| D-007 | Static capability composition before dynamic plugins | Planned | Narrow extension seams without speculative infrastructure |
| D-008 | Deterministic simulation consumes immutable validated snapshots | Required, pending | Replay and comparisons must not depend on hidden I/O or live model output |
| D-009 | No coding-agent attribution in new contributions | Applied policy | Explicit owner instruction; configured contributor identity remains authoritative |
| D-010 | MIT source license; repository public | Applied | The owner made the repository public on 2026-10-14; release contents still pass the privacy and redistribution review |
| D-011 | Python research and OR-Tools are optional boundaries | Planned | Scientific flexibility without a mandatory Python runtime in the core |
| D-012 | Tasteful code and comments require tools plus review | Applied policy | Formatting alone cannot verify rationale, correctness, or simplicity |
| D-013 | Desktop and CLI presentation follow the shared design kit in `design/` | Applied | One system across the owner's projects; the master at `../design-kit` is copied in so the repository stands alone |

## Making a new decision

Record the problem, chosen behavior, alternatives considered, evidence or benchmark,
consequences, and implementation status. Change contracts and acceptance gates with
the decision. Avoid locking in a library merely because it was named in an early plan.

For D-005, compare the same corpus, vector model, dimensions, filters, and queries.
Record cold/warm retrieval, peak memory, installed/index size, write/recovery behavior,
and relevance. Approximate retrieval needs recall against exact search. No benchmark
or default vector backend is claimed by this foundation.

## D-014 — Living cases and the decision OS thesis

28 October 2026. Direction accepted; runtime implementation pending.

Problem: evidence, simulation, commitments, and outcomes need continuity as the
world changes. Choose a living decision case composed by application services
over independent hdb and hsim libraries. Preserve frozen expectations alongside
current reasoning, distinct evidence states, explicit priorities, affected-person
outcomes, and optional models. Social responses and adoption feedback are explicit
model families with validation requirements.

Alternative: make chat, task lists, or a universal outcome score the primary object.
Those do not preserve the necessary reasoning and revision boundaries. Consequence:
source dependencies, simulation/execution conformance, information timing, and
conditional social-model interpretation become contract obligations. See
[THESIS.md](THESIS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
[VALIDATION.md](VALIDATION.md). The active gate remains deterministic cases.

## D-015 — Local planning and public acceptance contracts

28 October 2026. Applied to repository preparation.

Keep detailed sequencing and owner backlog in ignored `.local/BUILD_PLAN.md`.
Publish the thesis, status, contracts, and current acceptance gate so external
contributors can work without private files. This replaces the full public roadmap;
earlier versions remain in history. Do not mirror local planning into public issues
or releases. The tradeoff is that clones lack owner scheduling detail; assigned
tasks must therefore carry their own acceptance conditions.
