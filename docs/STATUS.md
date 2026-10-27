# Current status

28 October 2026. This file describes the current tree, not the preserved prototype.

| Area | Implemented now | Still to build |
| --- | --- | --- |
| hsim | Rust crate, crate documentation, workspace lints | Case validation, transitions, policies, simulation, analysis, replay |
| hdb | Rust crate, crate documentation, workspace lints | SQLite, evidence revisions, retrieval, artifacts, backup, model adapters |
| Application | Ownership and interface contracts | Shared services, CLI, desktop, commitments, review |
| Repository | CI, contributor rules, design kit, policy checks | Runtime conformance suites and application packaging as code arrives |

There are no runtime APIs, decision examples, model integrations, or usable v2
application. Empty-crate tests establish buildability only. CI configuration is
not evidence of a completed product or cross-platform desktop qualification.

## Current gate

**M1: contracts and a deterministic simulation slice.** Implement a versioned
synthetic case, exact time/resource semantics, and a minimal CLI demonstration.
The [acceptance gate](BUILD_PLAN.md) defines completion. No runtime milestone is
complete. Implementation is outside this repository-preparation change.

## Working branches

`main` owns the new implementation. `old` preserves the Python/React workstation
and lifesim snapshot. Historical behavior is reference material; its outputs do
not establish correctness for the rebuild. See [migration](MIGRATION.md).

Detailed owner planning lives in ignored `.local/BUILD_PLAN.md` when available.
Public issues and contracts provide sufficient scope for external contributions.
Do not copy the local backlog into public documents or issues.
