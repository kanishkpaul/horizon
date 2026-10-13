# Adding and removing abilities

Status: required lifecycle; no runtime capabilities are implemented yet.

## Inventory

| Ability | Owner | Required in core? | Planned boundary |
|---|---|---|---|
| Deterministic/stochastic simulation and analysis | hsim | Yes | Validated case and result APIs |
| Evidence, observations, revisions, backup, export | hdb | Yes | Workspace service and versioned records |
| Manual entry and lexical search | hdb | Yes | Importer and retrieval operations |
| Embeddings and vector retrieval | hdb | No | Embedding role and vector-index adapter |
| Chat/extraction and reranking | hdb | No | Role-specific model adapters |
| Domain dynamics | hsim | Selected by case | Declared state, resources, transitions, outputs |
| Advanced scheduling | Application | No | Solver worker protocol |
| Desktop/CLI | Application | Interface choice | Shared application services |
| Python bindings and media | Application/tooling | No | Engine binding or exporter |

## Capability contract

Every optional ability declares a stable ID and version, owner, configuration,
dependencies, permissions, consumed/produced data, resource limits, availability
probe, enable/disable behavior, migrations, and removal/export behavior. Begin with
a typed manifest in the composition root; do not add dynamic discovery by default.

The user-facing availability state distinguishes ready, disabled, missing dependency,
unsupported configuration, degraded, and failed. Hide or explain unavailable actions
without losing access to their persisted data. Do not confuse disablement with deletion.

## Addition checklist

1. State the decision or workflow improved and the smallest acceptance example.
2. Choose the owner and identify whether an existing seam is sufficient.
3. Define inputs, outputs, validation, errors, cancellation, and limits.
4. Declare permissions and default state. New network access is never implicit.
5. Add migrations and indexing intent if records change.
6. Test behavior, unavailable/disabled state, failure recovery, and no-model operation.
7. Measure added startup, memory, disk, and worker cost when material.
8. Update this inventory, build status, documentation, and the relevant ADR.

## Removal checklist

1. Stop accepting new jobs and cancel/drain active jobs safely.
2. Remove registration, optional dependencies, commands, and navigation.
3. Retain accepted evidence and outputs in readable versioned formats.
4. Make orphaned adapter configuration inert; never reinterpret it as another provider.
5. Offer explicit export/migration or deletion of derived artifacts. Do not silently
   delete source documents, credentials, or observations.
6. Test opening an old workspace without the removed ability and rebuilding indexes.
7. Remove stale comments and update capability status and contracts.

## Cargo features and runtime configuration

Use Cargo features for optional dependency inclusion, not user permissions. Cargo
features are additive and may unify across dependencies; model-provider selection
is runtime configuration. A minimal build must not acquire model or cloud dependencies
through a supposedly unrelated feature. Add no-default-feature and supported-feature
combination checks when the first optional dependency is introduced.

A trait belongs at a replaceable boundary, such as `VectorIndex`, not around every
operation. Keep SDK types inside adapters. Adding an importer should not require
editing the simulator; removing embeddings should not remove manual search.

Reference: [Cargo feature semantics](https://doc.rust-lang.org/cargo/reference/features.html).
