# Validation and performance

Status: foundation checks exist. Behavioral suites and benchmarks below are required
as their implementations arrive; none is claimed to pass for the empty libraries.

## Four different claims

| Claim | Required evidence |
|---|---|
| Implementation correctness | Analytic examples, invariants, counterexamples, integration/recovery tests |
| Retrieval and extraction quality | Held-out human labels, exact source support, filtering and error checks |
| Usability | Observed completion, comprehension, failures, and revisions by real users |
| Predictive or decision benefit | Prospective records, baselines, scoring, uncertainty, and an appropriate study |

Passing tests or running more worlds does not prove empirical model calibration.
Low Monte Carlo error says nothing by itself about omitted variables or causal effects.

## hsim checks

- Shared fractional deadlines conserve capacity across actions.
- Start/deadline overlap bounds effort; no work completes outside a valid window.
- Effects and responses become available in the specified order and timestamp.
- Graduation and horizon metrics use the exact declared cutoff.
- Policies see only available observations and preserve prerequisites/exclusivity.
- Fixed, Bernoulli, Beta, Normal, LogNormal, and other supported distributions reject
  invalid parameters and agree with analytic moments/quantiles within tolerance.
- Seeded streams survive changes to world batching, worker count, unrelated actions,
  and policy ordering; numerical reduction behavior is recorded.
- Mean/CVaR/quantile comparisons and uncertainty match their ranking criterion.
- Identical policies produce finite ties. Hard constraints govern search and regret.
- Complete snapshots replay; every behavior-affecting mutation changes identity.

## hdb and adapter checks

- Idempotent import, claim revisions, contradiction/supersession, and stable source spans.
- Atomic outcomes, parameter revisions, action states, and plan updates.
- Database migration, consistent WAL backup, export, restore, and corruption detection.
- Stale/deleted/unaccepted/unauthorized records cannot leak through vector results.
- Interrupted embedding changes and indexing queues recover without mixed generations.
- Disabled/removed capabilities retain records and have predictable degraded behavior.
- Model permission gates, credential redaction, streaming, cancellation, budgets, and
  error handling work with fake servers; no cloud fallback occurs in local mode.

## Retrieval evaluation

Create a synthetic/licensed corpus with held-out, human-labeled queries and graded
relevance. Include exact names/dates, semantic requests, negative cases, metadata
filters, and superseded evidence. Compare lexical, exact vector, hybrid, and optional
reranking on the same set. Report nDCG/recall, per-query failures, label uncertainty,
and latency. Approximate indexes also report recall against exact vector search.

The legacy twelve-query regex benchmark is a baseline artifact, not adequate proof
that a particular model or vector backend is best.

## Performance measurements

Measure cold/warm startup, idle total process-tree memory, core installed size,
optional model/solver size, indexing time, filtered retrieval p50/p95, simulation
latency, peak memory, archive writing, and cancellation latency. Record hardware,
OS, versions, corpus/model dimensions, actions/worlds/horizon, worker count, and
trace limits. Compare equivalent outputs and semantics.

A preliminary check of the legacy NumPy engine on 13 October 2026 measured two
strategies over 52 weeks: approximately 170 ms for 2,000 worlds and 1.25 s for
20,000 worlds (three-run medians). Process high-water memory was about 113 and
193 MiB. This excluded startup, model inference, decision analysis, and archive
writes. High-water memory is cumulative within the benchmark process. These are
orientation measurements, not v2 budgets or cross-language speedup claims.

Set regression budgets only after a repeatable v2 baseline. Keep models and expensive
workers unloaded until used. Measure minimal and optional-capability builds. A Rust
port must earn a performance claim with equal-work benchmarks.

## Continuous checks

The foundation runs rustfmt, Clippy, compilation/tests, rustdoc, Markdown link and
structure checks, and new commit-message policy checks. Empty-library tests verify
buildability only. Add behavioral suites at each milestone; add supported feature
combinations, minimum Rust version, and platform builds when dependencies/app exist.

## Prospective use

Record effort estimates and predictions before outcomes. Preserve resolution criteria,
pending responses, censoring, and revised estimates. Compare narrow repeated quantities
with simple baselines using proper scores and uncertainty. Do not infer causal effects
from selectively logged successes or a few personal attempts.

Reference: [proper scoring rules](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

## Continuity, social models, and analysis budgets

- A source revision exposes dependent current conclusions while old cases and
  forecasts retain the revisions used originally. Unknown applicability is explicit.
- Simulation and execution conformance fixtures agree on windows, shared resources,
  prerequisites, observation timing, completed work, and preserved user edits.
- All retrieval paths enforce the same review/visibility/temporal constraints,
  including negative cases and bounded traversal through cycles.
- Small games with known solutions check information sets, responses, feasibility,
  and multiplicity of equilibria where supported. Model solutions remain distinct
  from evidence of behavior by real people.
- Aggregate-feedback examples expose update rules, regime changes, convergence
  failures, and sensitivity rather than promise population forecasts.
- Analytic information-action cases include cost, delay, imperfect observation,
  and stopping conditions. Sensitivity alone is not an information-value estimate.
- Natural-unit outcomes for affected people remain visible under different explicit
  preference profiles. Analysis budgets report truncation and unexplored mechanisms.
