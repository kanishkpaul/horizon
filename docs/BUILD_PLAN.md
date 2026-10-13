# Build plan

Status on 13 October 2026: foundation prepared. All runtime milestones below are
pending. Work proceeds by acceptance gates, not an assumed calendar or simulated
progress. Each milestone ends with a runnable demonstration, tests, a reviewed diff,
and an update to this file.

## Foundation — complete

- Preserve all legacy tracked code and the lifesim snapshot on `old`.
- Preserve the historical audit and add an accurate legacy README.
- Back up ignored personal originals, SQLite, run archives, and media separately.
- Establish `hsim` and `hdb` as independent Rust library foundations.
- Write architecture, model, data, feature, validation, and contributor contracts.
- Add baseline formatting/lint/build/docs and repository-policy checks.

Completion means the empty workspace and documents are verified. It does not mean
the application, simulation, database, or model integrations are implemented.

## M1 — Contracts and deterministic simulation slice

Build hsim case validation, typed units and IDs, actions, preconditions, observed
state, exact time windows, resource capacity, and a deterministic transition loop.
Create a versioned JSON case format and a minimal CLI demonstration without models
or a database. Include unsupported-version and invalid-number rejection.

Acceptance:
- A synthetic case runs from validated input to natural-unit results.
- Shared deadlines and one-day windows cannot consume unavailable capacity.
- Event availability, prerequisites, and action ordering are explicit.
- Cutoff metrics use their exact definitions; hard constraints remain hard.
- No network, database, UI, or provider dependency exists in hsim.

Bring over reviewed legacy counterexamples, not the old engine wholesale.

## M2 — Authoritative evidence and workspace lifecycle

Build hdb SQLite migrations, sources, document storage, proposed and accepted claims,
supersession, observations, revisions, run storage, and workspace backup/export/restore.
Use synthetic fixtures. Add manual entry and basic document/text import.

Acceptance:
- A fresh workspace starts without old files or personal seeds.
- Reimporting identical content produces no duplicate records or relationships.
- Failed writes leave no partial outcome, action completion, or parameter change.
- Supersession retains history; conflicting evidence remains inspectable.
- Consistent backup/restore recovers records and referenced source artifacts.

## M3 — Local retrieval and replaceable vector storage

Build chunking with source spans, content hashing, lexical search, embedding/index
interfaces, and generation-aware indexing. Compare LanceDB OSS and sqlite-vec on
the same synthetic/licensed corpus. Select the default in an ADR only after measurement.

Acceptance:
- Source snippets resolve to their original locations.
- Filtering excludes unaccepted, stale, or unauthorized records as specified.
- Lexical search works without a downloaded model.
- Reindexing after a model change is resumable and cannot mix incompatible vectors.
- Measured relevance, filtering, latency, memory, disk size, and recovery justify
  the backend choice. Include exact vector search as a small-corpus baseline.

## M4 — BYOK and local model access

Build independent chat/reasoning, embedding, and reranking roles, native-provider
adapters where required, and a configurable compatible endpoint adapter. Support
no-model mode, local mode, BYOK mode, and deliberately configured mixed-role setups.
Add credential-store access, capability probing, context preview, streaming,
cancellation, errors, limits, redaction, and usage tracking.

Acceptance:
- Fake local and remote servers exercise protocol and failure behavior offline.
- API keys never enter records, logs, exports, or source control.
- Local-only policy rejects a remote route before any context is sent.
- No failed local request silently becomes a cloud request.
- Extraction creates reviewable proposed claims with sources, not accepted facts.
- A live adapter check occurs only with explicit authorization and budget.

## M5 — Stochastic policies, replay, and decision analysis

Add epistemic parameter draws, outcome randomness, versioned keyed streams, correlated
scenarios, adaptive policies, per-world metrics, downside measures, Pareto comparisons,
and feasibility-aware regret. Keep preference weighting explicit and optional.

Acceptance:
- Analytic examples and distribution tests agree within declared tolerances.
- Worker count, world batching, and unrelated actions do not alter keyed draws.
- Run identity includes every behavior-affecting input and algorithm version.
- Saved runs replay without consulting mutable current records.
- Mean, CVaR, and quantile comparisons use consistent explanations and uncertainty.
- Equal policies produce a finite, serializable tie. No infeasible candidate wins
  because of a finite score penalty.

## M6 — Application composition and first decision loop

Compose hdb and hsim through application services. Build the Tauri/React interface
and CLI around decision definition, evidence review, alternatives, assumptions,
comparison, selected actions, observations, and review. Reuse reviewed legacy UI
components only when they fit the new contracts. Keep transport types out of libraries.

Acceptance:
- A new user completes the first loop described in `PROJECT.md`.
- Core use works offline, without a model, account, or provider credentials.
- Expensive jobs never block interaction; cancellation and errors are visible.
- Changed inputs invalidate dependent results rather than displaying stale conclusions.
- Accessibility, keyboard use, and empty/error/loading states are checked in the UI.

## M7 — Feasible execution and prospective learning

Build a fourteen-day plan using real availability, remaining effort, dependencies,
and observed contingent activation. Integrate an optional OR-Tools worker through
a narrow protocol. Add plan diffs, duration observations, unresolved responses,
immutable forecasts, resolution criteria, and small-sample calibration.

Acceptance:
- Scheduling respects capacity, windows, dependencies, and accepted constraints.
- Regeneration preserves completed work and user edits; unrelated plans survive.
- Worker absence has an explicit reduced-capability path.
- Forecasts are recorded before resolution and compared with simple baselines.
- Pending/no-response observations are not silently treated as rejections.

## M8 — Adaptive pathways and useful information actions

Add decision thresholds, failure-scenario discovery, signposts, switching costs,
and information actions with imperfect observations, delay, and cost. Validate
regression EVPPI against analytic examples before adding EVSI. Start standard VOI
under expected utility; risk-sensitive extensions need their own derivation.

Acceptance:
- The app can explain when to change course and what to learn next.
- Advice links to the parameters, evidence, constraints, and observations that drive it.
- Robustness is conditional on the explored model ensemble, not a probability claim.
- Small experiments have explicit learning goals, cost, and stopping conditions.

## M9 — Broader domains, optional research tools, and public release

Adapt reviewed lifesim ideas into domain modules. Start with measurable time,
commitments, spending, runway, and user-reported energy. Add speculative dynamics
only with explicit assumptions and sensitivity tests. Add optional Python bindings
to the same hsim engine and optional media export if users need them.

Acceptance:
- Domain composition does not double-count resources or effects.
- Feature removal follows `FEATURES.md` and retains user data.
- Installers, backup/recovery, no-model workflows, and resource budgets are checked
  on macOS, Windows, and Linux.
- Pilot users can understand and use the loop; outcome benefits are not inferred
  from a small usability pilot.
- Release contents, history, licenses, models, and fixtures pass the privacy and
  redistribution review. Publishing the repository remains a separate action.

## Working rhythm

Keep one current milestone and a small queue of concrete behavioral tasks. Ship
reviewable slices weekly when feasible. Record actual checks and limitations.
Do not mark a milestone complete because its scaffolding exists. Update the
capability inventory, ADRs, and relevant contracts in the same change.
