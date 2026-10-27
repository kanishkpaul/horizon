# hsim

Horizon's independent simulation and decision-analysis library. It consumes validated
case snapshots and evaluates adaptive policies under explicit resource and uncertainty
assumptions. It does not depend on hdb, Tauri, model providers, or network access.

Current status: empty library foundation, with no runtime API. Start with M1 in
[the current acceptance gate](../docs/BUILD_PLAN.md). Read [the contract](../docs/HSIM.md),
[coding standard](../docs/CODE_STYLE.md), and [scoped instructions](AGENTS.md).

Future private modules should follow actual responsibilities: model validation,
time/resources, transitions, stochastic sampling, policies, analysis, and replay.
Create modules when their implementation arrives rather than adding empty interfaces.
