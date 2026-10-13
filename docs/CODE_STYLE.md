# Coding and commenting standard

Required for every contributor and coding assistant. Read before implementing or
reviewing code. This is Horizon's synthesis of the primary guidance linked below;
it does not adopt another project's conventions wholesale.

## What good code looks like here

The reader should find the domain behavior, invariant, and failure path without
tracing through a framework. Choose the smallest clear design that implements the
current requirement. An extension seam is useful when an actual dependency can be
replaced; an abstraction with no concrete need is extra work for every reader.

- Name domain concepts precisely: `remaining_effort`, `deadline`, `source_revision`.
  Avoid `manager`, `helper`, `processor`, and `utils` when the responsibility can be named.
- Make units, IDs, statuses, and invalid states explicit. Validate finite numbers,
  probability bounds, distribution parameters, time windows, and schema versions.
- Prefer early validation and linear control flow. A short function that hides
  five implicit side effects is worse than a longer cohesive function.
- Keep modules cohesive and dependency direction visible. Extract a function or
  module when it names a real operation, invariant, or ownership boundary. Do not
  impose arbitrary line-count limits or split a readable operation to meet a quota.
- Keep public interfaces small and implementation details private. Avoid duplicated
  validation and competing representations of the same rule.
- Use typed errors with actionable context. Do not catch everything and continue,
  panic for ordinary input errors, or advertise a partial result as success.
- Bound memory, workers, retries, response sizes, and job duration. Cancellation
  is behavior to design, not a later flag.
- Prefer ordinary control flow over clever compression, custom macros, or a generic
  framework. Add complexity only when a concrete requirement or measurement warrants it.

## Rust

Follow rustfmt and the Rust API Guidelines where they serve the API. Use newtypes
for values whose units or validity matter and enums for domain states. Fallible
constructors must enforce invariants; public fields must not bypass them.

Borrow data where ownership is clear. Clone deliberately, not to silence a lifetime
problem without understanding it. Do not force everything through `Arc<Mutex<_>>`.
Choose concrete types inside a module and traits at real adapter boundaries.

Return `Result` for expected failures. Production `unwrap`/`expect` needs a genuine
invariant and review; prefer making that invariant explicit in the type. Test setup
may use them when a failure should fail the test. The workspace lint flags uses.
Unsafe code is forbidden in the foundation. A future FFI exception must be isolated,
documented, tested, and recorded in an ADR rather than enabled across a library.

Public APIs document purpose, relevant units, behavior, errors, and an example where
it helps a caller. Document panics or safety requirements only when applicable.
Link related types and examples rather than repeating implementation details.
Use `//!` for module/crate contracts and `///` for public API documentation.

## TypeScript and UI

Use strict types and explicit boundary parsing. Prefer `unknown` with validation
to `any`. Components own interaction and presentation, not database or simulation
semantics. Keep state transitions, loading/error/empty states, request cancellation,
and invalidation explicit. Use existing project formatting tools once the app exists.

Name a reusable component for its behavior or domain, not a vague visual container.
Extract when it has a coherent responsibility; do not build a component factory for
every piece of markup. Avoid incidental memoization or state-management libraries
without evidence that they improve the real flow.

## Comments

Comments preserve information the code cannot express well: a reason, model
assumption, subtle invariant, algorithm interpretation, or compatibility constraint.
Public documentation describes the contract; inline comments explain a non-obvious
choice in its implementation. These are different jobs.

Before writing a comment, ask whether a better name, type, or simpler expression
would remove the need. Keep remaining comments accurate and near the relevant code.
Prefer one specific sentence over a paragraph of narration.

```rust
// The deadline ends the window; work at or after it must not count toward completion.
```

That conveys an important temporal convention. A comment such as `// Check the
deadline` merely repeats an operation's name and should be removed.

For scientific code, state what a coefficient assumes, its unit, and where its
derivation or evidence lives. Distinguish an empirical estimate from a scenario
assumption. Explain event ordering, common random numbers, tail direction, and
reduction semantics where they are not apparent from types.

Do not add decorative banners, numbered tours through ordinary code, redundant
function summaries, commented-out implementations, change diaries, author/model
signatures, or unsupported claims such as "optimal" and "thread-safe". Remove stale
comments in the same change that invalidates them. Put long derivations in a focused
document and link it from the code.

A TODO must identify a specific unresolved behavior and a tracked issue or build
milestone. `TODO: improve this` is not actionable. Workarounds name their trigger
and removal condition; do not create a generic warning above every function.

## Tests and review

Test observable contracts, analytic answers, invalid inputs, counterexamples,
transactions, and recovery. Use deterministic fixtures and fake providers. Avoid
tests that only reconstruct the same implementation or verify a mock was called.

In review, ask whether the diff makes behavior easier to understand, preserves the
boundary, handles failures, and proves the important invariant. Review comments
should identify a concrete correctness or maintenance concern; separate preferences
from requirements. Formatting and linting are necessary but cannot verify taste.

Never add coding-agent co-author trailers, generated-by signatures, or coding-agent
attribution. Legitimate third-party copyright and license notices remain required.

## Research used for this standard

Read on 13 October 2026. The rules above are project decisions, informed by:

- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/): interoperable,
  predictable APIs and deliberate visibility.
- [Rust type-safety guidance](https://rust-lang.github.io/api-guidelines/type-safety.html):
  distinct types for units and semantic differences.
- [Rust documentation guidance](https://rust-lang.github.io/api-guidelines/documentation.html)
  and [the Rust Book](https://doc.rust-lang.org/book/ch14-02-publishing-to-crates-io.html):
  public contracts, examples, and applicable failure documentation.
- [Google's code-review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html):
  simplicity, domain names, useful tests, and comments about rationale.
- [Google's TypeScript guide](https://google.github.io/styleguide/tsguide.html):
  consistent types, naming, and the distinction between comments and API documentation.
- [Linux kernel commenting guidance](https://docs.kernel.org/process/coding-style.html#commenting):
  restraint and explanatory purpose. Its C formatting rules do not apply to Horizon.

The instruction files make reading this standard mandatory. CI checks formatting,
linting, repository structure, and commit policy. Contributors still need to review
the meaning and accuracy of their code and comments.
