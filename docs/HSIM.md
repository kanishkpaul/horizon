# hsim contract

Status: design contract; no runtime API is implemented yet.

hsim is Horizon's simulation and decision-analysis library. It evaluates policies
under explicit assumptions and reports conditional outcomes and tradeoffs.

## Inputs

A validated, immutable case snapshot contains:

- Schema version, stable case ID, revision, time origin, horizon, and cutoff definitions.
- Observed initial state, including observation uncertainty where justified.
- Actions, exact windows, resource demands, prerequisites, mutually exclusive choices,
  completion effects, staged responses, and external events.
- Parameter distributions with units, origin, source references, and transfer caveats.
- Policies with priority and observable conditions for enabling/disabling actions.
- Resource availability, concurrent limits, disruption assumptions, and domain modules.
- Natural-unit metrics, optional value profiles, hard constraints, and risk criteria.
- Seed, random-stream algorithm version, worker/batch configuration, and trace limits.

Reject missing references, invalid distributions, non-finite numbers, impossible
windows, ambiguous units, and unsupported schema versions before evaluation. Unknown
facts are represented explicitly rather than invented by a compiler.

## Execution semantics

Separate action completion from external success. Events become available only at
their declared timestamps. A policy sees observed state to that point, never future
random draws. Shared capacity is consumed once across all actions; overlap windows
and prerequisites determine when effort can be assigned.

Keep epistemic parameter uncertainty, aleatoric outcomes, structural scenarios,
and Monte Carlo sampling error distinct. A positive noise floor cannot represent
all unknown mechanisms. More worlds reduce sampling error, not model error.

Use versioned keyed streams for paired policy comparisons. A world/action/event
identity must not depend on iteration order, batch size, or worker scheduling.
Document distribution-sampling and floating-point reduction semantics. Changing
the algorithm or numerical behavior creates a new engine version. Cross-platform
bitwise replay is not promised unless tested; otherwise publish its tolerance.

## Results and replay

Return natural-unit distributions, feasibility, selected traces, diagnostics,
warnings, and limitations. Keep full arrays separate from UI summaries. Record the
complete case, model and policy specs, parameter distributions, accepted evidence
revision, initial observations, calendar, objective, engine version, random-stream
version, seed, and archive hashes. A fingerprint includes every behavior-affecting
field; a saved run cannot rebuild itself from today's mutable catalogue.

Mean, quantile, and CVaR rankings require comparisons and uncertainty estimates for
that same criterion. Hard constraints cannot become a finite optimization penalty.
Report ties explicitly with finite serializable values. Minimax regret only compares
the declared feasible choices under the declared scenario treatment.

Preference weighting is explicit and optional. Multi-domain outputs remain visible;
no hidden life score or population worth ranking is allowed.

## Domain modules and extension

A domain module declares state variables, units, resource ownership, transition
rules, events, metrics, parameters, evidence origins, and compatibility. Composition
rejects duplicate resource consumption and conflicting state/effect ownership.
Adding a domain does not grant network access or introduce storage into hsim.

## Required checks

See `VALIDATION.md`: exact resource/window tests, analytic stochastic examples,
paired-stream invariants, cutoff tests, consistent risk explanations, replay,
invalid input rejection, and feasible search/regret behavior. Legacy failures are
synthetic regression cases, not a reason to preserve incorrect outputs.

## Research direction

Robust planning compares choices across plausible assumptions; adaptive pathways
attach signposts and contingent changes; information analysis asks what observation
could change a decision. Start with simple validated implementations and document
their limits before optimization or broader domains.

References: [Robust Decision Making](https://link.springer.com/chapter/10.1007/978-3-030-05252-2_2),
[adaptive pathways](https://ris.utwente.nl/ws/files/247793059/Haasnoot2013dynamic.pdf),
[regression EVPPI](https://journals.sagepub.com/doi/10.1177/0272989X13505910),
[EVSI](https://journals.sagepub.com/doi/10.1177/0272989X15575286).
