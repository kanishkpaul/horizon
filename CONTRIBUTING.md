# Contributing

Read `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/CODE_STYLE.md` first. They apply
to human-written and assisted contributions alike.

## Development

The initial workspace contains two empty Rust library foundations, `hsim` and
`hdb`. Use stable Rust with edition 2024 support (Rust 1.85 or newer). CI checks
current stable; a minimum-version check must be added when dependencies are chosen.
No toolchain, dependency, runtime, or desktop performance beyond that has been
qualified yet.

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo doc --workspace --no-deps
python3 scripts/check_repository.py
git diff --check
```

Add component and no-default-feature checks when optional capabilities arrive.
Use locked dependencies in CI. TypeScript type checking, linting, UI tests, and
cross-platform desktop packaging join CI when the app is introduced, not before.

## Changes and review

Describe the concrete behavior, why it belongs in the project, and how it was
verified. Distinguish numerical agreement from empirical validation. Keep fixes,
formatting-only changes, and new capabilities separate when that aids review.

Every capability addition or removal follows `docs/FEATURES.md`. Public API changes
need contract updates; storage changes need migration and recovery tests; model
adapters need cancellation, error, and context-permission checks.

Review for design, correctness, concurrency, clear names, unnecessary abstraction,
bounded resource use, and useful comments. Automated tools cannot certify taste
or prove a comment's rationale is accurate. Human review remains necessary.

## Commits and authorship

Use your configured Git identity and a short, factual subject. Never add coding-agent
co-author trailers, generated-by signatures, or coding-agent attribution to commits,
pull requests, documentation, or source. The repository check rejects attribution
patterns in the commit messages it examines; inspect prose manually as well.
`.commit-policy-base` records the immutable legacy preservation commit. CI examines
every descendant commit after that baseline, so it enforces the new rule without
rewriting historical metadata. Do not move that baseline to hide a violation.
Third-party
copyright and license notices must remain intact.

## Data and models

Use synthetic fixtures and offline fake providers in tests. Do not send real user
context to a model for testing. A live paid/model integration check requires separate
authorization and an explicit budget. API keys and personal data stay outside Git.

## Branches

`main` is active v2 development. Use focused branches or direct commits according
to the user's requested workflow. `old` preserves the legacy implementation and
is not merged back wholesale. This repository is currently private; making it
public is a separate action after the release review in `docs/MIGRATION.md`.
