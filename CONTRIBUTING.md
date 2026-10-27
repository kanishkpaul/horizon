# Contributing

Horizon is being built as an open-source, local-first decision OS. Start with
[the thesis](docs/THESIS.md), [current status](docs/STATUS.md),
[AGENTS.md](AGENTS.md), and [the coding standard](docs/CODE_STYLE.md).
The public repository currently provides contracts, tooling, and two empty Rust crates.

## Make a change

1. Define the user behavior, owning module, capability boundary, and acceptance check.
2. Read the relevant library contract and scoped instructions before implementation.
3. Implement a small, complete slice with meaningful behavioral checks.
4. Update affected contracts, capability status, and decisions in the same change.
5. Run applicable checks and review the diff for private data, stale claims,
   unnecessary abstraction, dependencies, comments, and attribution.

The detailed owner plan stays in ignored `.local/BUILD_PLAN.md`. Read it when
available for an assigned implementation task; a clone does not need it.
Use the task's acceptance conditions and public contracts. Never publish the
local backlog or scratch research in docs, issues, pull requests, or releases.

## Check the foundation

Use Rust 1.85+ with edition 2024 support and Python 3.11+. CI checks stable Rust
on Linux, macOS, and Windows, plus minimum Rust on Linux. These are foundation
checks; desktop packaging and runtime conformance are not implemented.

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
RUSTDOCFLAGS="-D warnings" cargo doc --locked --workspace --no-deps
python3 scripts/check_repository.py
python3 -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

Use locked dependencies in CI. Add feature-combination, application, and packaging
checks when those capabilities exist. Empty-crate tests prove buildability only.
No private dataset, model, key, or paid request is needed for these checks.

## Contracts and review

Simulation changes need analytic answers, invariants, and counterexamples.
Storage changes need idempotence, rollback, migration, and recovery checks.
Provider changes need offline fake-server tests for permissions, limits,
cancellation, errors, and local-to-cloud fallback prevention.
Documentation changes need link, consistency, policy, and diff checks.

Every capability addition or removal follows [FEATURES.md](docs/FEATURES.md).
Architecture changes belong in [DECISIONS.md](docs/DECISIONS.md), with affected
contracts and the acceptance gate updated. Review code for bounded resource use,
clear domain names, typed invariants, and comments explaining non-obvious reasons.

## Commits and authorship

Install the local commit-message hook:

```sh
git config --local core.hooksPath .githooks
```

Use your configured contributor identity and a short factual subject, such as
`hsim: reject effort outside action windows`. Never add coding-agent co-author
trailers, generated-by signatures, or coding-agent attribution to commits,
pull requests, documentation, or source. Retain third-party license notices.

The hook checks the proposed commit message; CI checks descendants of the fixed
legacy baseline in `.commit-policy-base`. Do not move it to hide a violation or
rewrite historical metadata. To inspect a specific new range:

```sh
python3 scripts/check_repository.py --commit-range BASE..HEAD
```

Replace `BASE` with the actual integration base. Review changed prose manually;
a pattern check cannot establish correct authorship or factual accuracy.

## Data and branches

Use synthetic or redistribution-licensed fixtures. Keep personal originals
read-only and outside Git. SQLite WAL backups must use a consistent snapshot.
Live model calls and paid usage need direct authorization and a budget; ordinary
tests must run offline with fakes. Do not contact people or submit anything as
part of a repository test.

`main` owns new development; focused review branches may land there. `old`
preserves the legacy implementation and must not be merged wholesale.
Horizon is already public. Release review and the historical-data boundary are
documented in [MIGRATION.md](docs/MIGRATION.md); public source is not a qualified
product release.
