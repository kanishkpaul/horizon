# Architecture

Status: agreed design; only the two empty Rust library crates are implemented.

## Boundaries

| Component | Owns | Does not own |
|---|---|---|
| `hsim` | Model validation, action transitions, capacity, stochastic execution, policy comparison, analysis, replay semantics | Databases, credentials, network calls, provider SDKs, UI, real-world execution |
| `hdb` | Evidence, claims, observations, workspace revisions, indexes, retrieval, documents, model-access adapters, archive storage | Simulation transitions, utility judgments, autonomous acceptance of model output, UI |
| Application | Case assembly, accepted changes, capability permissions, jobs, planning/execution UX, desktop and CLI | A second simulator or a second evidence authority |

Neither core library imports the other. The application turns accepted hdb records
into a validated hsim case. It stores hsim outputs as versioned artifacts through
hdb. Similar names in two libraries do not justify duplicate semantics: shared
transport formats in `schemas/` define stable IDs, units, statuses, and versions.
Mapping remains explicit at the application boundary.

## Workspace layout

```text
hsim/                 simulation library and scoped instructions
hdb/                  evidence/retrieval library and scoped instructions
apps/                 desktop and CLI composition (planned)
schemas/              versioned interchange contracts (planned)
examples/             synthetic decision cases (planned)
scripts/              repository checks
docs/                 thesis, status, contracts, active gate, standards, decisions
.local/               ignored owner planning; absent from public clones
```

Start each library with private modules, a small public API, and tests alongside
the behavior. Do not pre-create dozens of empty crates or a generic plugin runtime.
Extract a crate when a capability has a real independent dependency or lifecycle.

## Data flow

An imported source creates a preserved document record. Parsing and optional model
extraction create proposed claims linked to exact source locations. A reviewed claim
revision becomes accepted evidence. The application assembles a case snapshot from
accepted evidence and declared assumptions. hsim validates and evaluates it. The
application presents alternatives and persists a run manifest and arrays through
hdb. Real outcomes create observations, not edits to simulated history.

Every transition across that flow is typed and inspectable. Model output cannot
silently become accepted evidence or a simulation parameter. Similarity is a
retrieval signal, never proof of a fact, eligibility, causation, or identity.

## Storage and retrieval

SQLite is the authoritative transactional record. An embedded vector backend is a
replaceable derived index. Each chunk has a stable source ID, source location,
content hash, embedding model revision, dimensions, normalization/metric definition,
and index generation. Rebuild indexes from records; do not make them the only copy.

With separate SQLite and vector stores, use a durable indexing queue/outbox and
generation checks. Commit authoritative changes and indexing intent in one SQLite
transaction. Exclude stale/superseded records at query time, retry idempotently,
and recover from interruption without advertising a stale index as current.

Benchmark LanceDB OSS and sqlite-vec behind the same operations before selecting
the default. Keep lexical retrieval working when embeddings are absent.

## Jobs and performance

Desktop invokes application commands through Tauri IPC; CLI uses the same services.
Core libraries remain independent of the transport. CPU jobs run on bounded workers,
with cancellation at batch boundaries, progress, and atomic publication of results.
Do not hold a database write transaction while a model or simulation runs.

The default application should not load a model, start a solver, or launch a media
renderer at startup. Prevent nested worker pools from oversubscribing the machine.
Return summaries and selected traces to the UI; keep large arrays out of IPC JSON.
Chunking, storage layout, and reduction order are part of benchmark and replay design.

## Extension boundaries

Replaceable boundaries are document importers, vector indexes, model roles, rerankers,
domain model modules, solver workers, and media exporters. Give each a narrow contract
and a manifest listing dependencies, permissions, configuration, data, and removal
behavior. Keep a static composition root initially. Runtime discovery, dynamic
library loading, and a universal event bus require a demonstrated use case.

Core data contracts survive feature removal. Optional adapters must not leak their
SDK types into those contracts. See `FEATURES.md` for the full lifecycle.

## Dependencies

Rust, Tauri 2, TypeScript/React/Vite, SQLite, and optional numerical/model/solver
libraries form the target stack. No microservice infrastructure is required for a
local workspace. Add Python bindings and an OR-Tools worker only at their milestones.
Dependencies and models need licensing and distribution checks before release.

References: [Tauri architecture](https://v2.tauri.app/concept/architecture/),
[SQLite application guidance](https://www.sqlite.org/whentouse.html),
[LanceDB OSS](https://docs.lancedb.com/),
[sqlite-vec](https://alexgarcia.xyz/sqlite-vec/).

## Case continuity and consequences

The application owns the living decision case and maps current hdb revisions to
frozen hsim inputs. A run and commitment retain the revisions used at the time.
New evidence marks dependent current results for review; it cannot mutate saved
expectations or completed actions. Simulation and execution share explicit time,
resource, prerequisite, and information-availability contracts through the
application mapping and conformance fixtures.

Support, contradiction, and dependency edges belong to hdb. A support edge records
a stated relationship; it does not prove logical entailment or causal effect.
Social mechanisms, other actors' policies, and aggregate-response scenarios belong
to hsim's explicit input model. The application owns whose priorities are applied
and displays outcomes for affected people separately. Model refinement and stopping
choices belong to application orchestration; hsim remains bounded and free of I/O.
