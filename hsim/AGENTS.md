# hsim instructions

Follow root `AGENTS.md` and `docs/CODE_STYLE.md`. Read `docs/HSIM.md` before changes.

- Keep this library independent of hdb, UI frameworks, databases, providers, and network.
- Validate immutable case inputs before running. Use explicit units, references,
  time conventions, and observation availability.
- Preserve shared capacity, exact cutoffs, policy information boundaries, keyed
  randomness, feasibility, and complete replay identity.
- Numerical semantics and causal assumptions need concise rationale comments with
  links to evidence or derivations when relevant. Do not narrate ordinary loops.
- Tests need analytic answers or meaningful counterexamples. Match the ranking
  statistic in explanations and uncertainty estimates; serialize ties finitely.
- Social response models declare actors, information, incentives, and assumptions;
  equilibria remain conditional results. Information actions include cost and delay.
- Broader domains must declare resource ownership and avoid double-counting.
- Never add coding-agent attribution or co-author trailers.
