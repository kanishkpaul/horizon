# Current acceptance gate

The detailed owner build plan is local-only at `.local/BUILD_PLAN.md`. It is not
part of a clone, release, or contribution requirement. This public document keeps
only the active implementation gate; [status](STATUS.md) records what exists.
Earlier public roadmap versions remain in Git history.

## M1 — Contracts and a deterministic simulation slice

User behavior: compare three policies for a synthetic decision with competing
uses of time, a prerequisite, an exact deadline, and a delayed observation.

Owners: hsim validates and evaluates the immutable case; a minimal application
CLI handles files and presentation. Versioned interchange contracts belong in
`schemas/`; redistributable fixtures belong in `examples/`.

Acceptance:

- Typed units, IDs, exact time windows, capacities, prerequisites, effects, and
  observation availability have explicit validated semantics.
- Invalid numbers, references, units, and unsupported versions fail before execution.
- Shared fractional windows cannot overspend capacity; hard constraints remain hard.
- Policies see only information available at the current simulation time.
- The CLI reports conditional natural-unit results with no database or model required.
- Analytic examples and synthetic counterexamples check event ordering, resource
  conservation, deadlines, invalid inputs, and repeatability.
- hsim remains independent of hdb, network, providers, databases, and UI frameworks.
- Contracts, capability status, and actual check results accompany the implementation.

This gate is pending. A source skeleton or passing empty-crate test does not
complete it. Start from the [hsim contract](HSIM.md) and
[validation requirements](VALIDATION.md), not a wholesale legacy port.
