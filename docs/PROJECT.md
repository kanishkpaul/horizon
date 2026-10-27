# Project scope

Horizon helps a person reason about alternatives, make feasible near-term
commitments, and adapt to evidence. It is an open-source, local-first decision OS:
infrastructure connecting
knowledge, possibilities, commitments, and experience. "OS" describes this decision
workflow; Horizon is an application and reusable libraries, not a host operating
system. Read [the thesis](THESIS.md) for the full direction.

## Living decision cases

A case links evidence, assumptions, alternatives, resources, policies, commitments,
and observations. Current reasoning can change while historical cases and prior
expectations remain frozen. Decisions expose user priorities and consequences for
affected people; there is no hidden aggregate measure of a person's worth.

## The useful loop

1. Define a decision, desired outcomes, constraints, and review date.
2. Collect evidence, record unknowns, and propose alternative actions.
3. Compare policies under inspectable assumptions and resource limits.
4. Identify failure conditions, decision thresholds, and useful information actions.
5. Choose a feasible near-term plan; preserve options and contingencies.
6. Record actual effort and outcomes, then revise from observed state.

The first domain is research and career planning. Broader project, money, energy,
and relationship tradeoffs are later domain modules with declared measurement and
model assumptions. No domain gets a hidden universal life score.

## Two parts

`hsim` owns simulation and decision analysis. `hdb` owns evidence, durable records,
retrieval, and model access. They are independently usable libraries. The application
composes them and owns interaction, permissions, case assembly, and execution.

## Product commitments

- Free and open-source core under MIT. No account or hosted subscription is needed.
- Local ownership, portable workspaces, explicit export, backup, and recovery.
- BYOK and local model compatibility through independent role-specific adapters.
- Chat/reasoning, embeddings, and reranking can use different model configurations.
- Essential workflows function without a model. AI proposes; validated code computes.
- Optional abilities can be added, disabled, replaced, and removed predictably.
- Speed and footprint are measured across the complete application, including
  workers, WebViews, downloaded models, and indexes.

Free source does not make provider inference or operating-system distribution free.
Do not disguise a paid dependency as part of the offline core.

## First complete demonstration

A new user opens a synthetic or empty workspace, defines a decision, compares three
paths, sees the assumptions that change their choice, produces a feasible fourteen-day
plan, and revises it after recording what happened. The no-model path and at least
one local and one BYOK adapter are tested separately with fake providers before any
live integration check.

## Status and deferred scope

The current tree provides instructions, contracts, an acceptance gate, and empty Rust
library foundations. It implements none of the loop above yet. See
[current status](STATUS.md) for the implementation inventory. Desktop UI, provider
integration, simulation, storage, and retrieval are future milestones.

Autonomous outreach, general-purpose shell execution, cloud collaboration, clinical
prediction, trading advice, and population ranking are outside the initial scope.
Expand only after a concrete decision benefit and evidence justify the addition.

## Research boundaries

Social reasoning uses explicit, revisable models of other actors' information,
incentives, and responses. Cooperation, bargaining, signalling, competition,
and adoption feedback are part of the direction, with their own validation gates.
Model equilibria do not establish how real people will behave.

Analysis should focus on unknowns that could change a commitment, with visible
attention and computation budgets. Information actions account for cost, delay,
and imperfect observations. Novel methods and decision benefit require evidence;
the thesis alone establishes neither.
