# Methodology registry

Methods were investigated broadly and implemented selectively. Classes: **Essential** (core, implemented), **Useful** (implemented or planned), **Experimental** (promising, not validated here), **Unnecessary** (adds complexity without decision value at this scale), **Inappropriate** (needs data or assumptions this problem lacks).

| Method | Source | Class | Status in Horizon | Why / failure mode |
|---|---|---|---|---|
| Stochastic state-transition model over an AND/OR action graph | Planning literature (STRIPS-style preconditions/effects; AND/OR graphs, Nilsson 1980) | Essential | `sim/engine.py` | Captures simultaneous prerequisites, alternatives and actions that create new actions. Fails if the action catalogue misses important actions |
| Monte Carlo with epistemic draws per world + aleatory outcomes | Standard Bayesian predictive simulation | Essential | Implemented | Separates "unknown rate" from "luck", which EVPPI needs. More worlds only reduce sampling error, not model error |
| Common random numbers | Law & Kelton, *Simulation Modeling and Analysis* | Essential | Keyed RNG streams | Paired comparisons between strategies have far lower variance |
| Latent-factor correlation (Gaussian factors, logit loadings) | Factor/copula models | Useful | `portfolio`, `market` factors | Avoids treating applications as independent. Loadings are scenario assumptions |
| Adaptive policies (priority list + condition→enable/disable rules) | Contingent planning; dynamic treatment regimes | Essential | `Strategy.rules` | Output is a policy, not a timeline. Rules only see the past, so there is no look-ahead |
| MDP / POMDP exact solution, reinforcement learning | Puterman 1994; Kaelbling et al. 1998 | Inappropriate | Not used | The state space is huge, transition probabilities are mostly judgment, and there is a single decision-maker with no repeated episodes; an exact policy would be optimising noise |
| Evolutionary multi-objective search (NSGA-II) | Deb et al. 2002 | Useful | `strategy_search.py` | Finds policies nobody hand-designed. Risk: exploits model blind spots, so results are adversarially reviewed |
| Monte Carlo tree search | Browne et al. 2012 | Experimental | Not used | Useful if the policy had to react week by week to observed outcomes beyond rule triggers |
| Resource-constrained scheduling with critical-ratio priority | Project scheduling (EDF / critical ratio) | Essential | Weekly allocator | Simple and explainable. Not optimal; CP-SAT would find better week plans |
| CP-SAT / MILP schedule optimisation | Google OR-Tools | Useful | Installed, not wired | Best fit for a short-horizon (14–30 day) concrete calendar; planned for the cockpit |
| Pareto frontier / dominance | Multi-objective optimisation | Essential | `analysis.pareto_front`, paired dominance | Shows choices that are never right under any weighting |
| Multi-attribute utility with saturating scales + weights | Keeney & Raiffa 1976; value-focused thinking (Keeney 1992) | Essential | `objectives.yaml` | Weights express values, not exchange rates. Caps prevent one metric dominating, but also reward breadth (see adversarial review) |
| Lexicographic / hard constraints | Decision analysis | Essential | Constraint checks → infeasible | Keeps non-negotiables out of trade-offs |
| CVaR / quantile risk measures | Rockafellar & Uryasev 2000 | Useful | `risk.measure` | Judges a policy by its bad worlds |
| Minimax regret across model variants | Savage 1951; robust decision-making (Lempert et al. 2003) | Essential | `analysis_jobs.scenario_regret` | Handles structural (not just parametric) uncertainty |
| Distributionally robust optimisation | Delage & Ye 2010 | Unnecessary | Not used | Regret across explicit variants answers the same question more transparently |
| Value of information (EVPI / EVPPI) | Howard 1966; Strong & Oakley 2014 (regression EVPPI) | Essential | Binned EVPPI with permutation noise floor | Says which question to answer first. Biased upward with small bins, hence the floor |
| One-at-a-time and global sensitivity (tornado, Spearman) | Saltelli et al. 2008 | Useful | Implemented | Misses interactions; Sobol indices would capture them at higher cost |
| Bayesian updating from own outcomes (Beta–binomial, power prior) | Ibrahim & Chen 2000 | Essential | `execution.calibrate` | Down-weights a handful of personal outcomes; reversible |
| Hierarchical Bayesian pooling across outreach types | Gelman et al., *BDA* | Useful | Planned | Needs ≥ a few dozen logged attempts first |
| Proper scoring rules (Brier, log loss), calibration bins | Brier 1950; Gneiting & Raftery 2007 | Useful | Forecast panel | Noisy with few resolved forecasts |
| Structural causal models / do-calculus | Pearl 2009 | Useful (conceptual) | Evidence effects encoded as explicit causal assumptions (logit shifts) with uncertainty that includes zero; "evidence has no effect" variant | Effects are not identified from data. Observational referral gaps (≈11×) are discounted for selection |
| Causal discovery from data | Spirtes, Glymour & Scheines | Inappropriate | Not used | No longitudinal data about this person |
| Graph algorithms (shortest path, centrality, max-flow) | Network science | Unnecessary as a core | Unlock map is a DAG visualisation | Career paths need AND-prerequisites and stochastic outcomes; a shortest path is the wrong question (validation test 8) |
| Weak ties / structural holes | Granovetter 1973; Burt 1992; Rajkumar et al. 2022 | Useful | Ties metric; per-tie value small; outreach modelled as many draws | Per-tie job probability is ~0.1%; do not over-weight single contacts |
| Signalling / screening, human capital | Spence 1973; Becker 1964 | Useful (conceptual) | Evidence → selection shifts | Explains why public artifacts and peer review shift odds |
| Real options / value of waiting | Dixit & Pindyck 1994 | Useful | Contingent rules; Oct-vs-Jan analysis | Deferral can dominate when an option is cheap to keep |
| Search & matching, optimal stopping | Mortensen & Pissarides; Ferguson | Experimental | Not used | Relevant when offers must be accepted or rejected sequentially (spring 2027) |
| Game theory / agent-based models of evaluators | — | Inappropriate | Not used | Would require inventing private intentions of real people |
| Planning fallacy / reference-class forecasting | Buehler et al. 1994; Flyvbjerg 2006 | Essential | `effort_bias`, heavy-tailed noise | Self-estimates are optimistic; calibrate from your logged durations |
| Hours–output concavity | Pencavel 2014 | Useful | Linear to 49 h, 0.4 marginal to 63 h, flat beyond | From munitions workers; a scenario assumption for knowledge work |
| AI productivity evidence | Peng et al. 2023; Dell'Acqua et al. 2023; METR 2025 RCT | Essential | Multiplier only on the automatable share; adverse 0.85, central 1.25 | Evidence ranges from −19% to +56% |
| Task-switching costs | Rubinstein, Meyer & Evans 2001; Monsell 2003 | Useful | Switch cost beyond focus_k; quality-dilution variant | Lab-scale results; transfer to multi-week projects is uncertain |
| Learning curves (exponential vs power) | Newell & Rosenbloom 1981; Heathcote et al. 2000 | Experimental | Not used | Skill-building actions are coarse tokens |
| Sleep restriction effects | Van Dongen et al. 2003 | Useful (as a constraint) | Not modelled as a lever | The model never recommends trading sleep for hours |
| System dynamics / cumulative advantage | Sterman 2000; Merton 1968 | Experimental | Feedback appears via tokens (outputs → odds → offers → referrals) | Compounding is explicit, not assumed exponential |
| Hybrid retrieval (BM25 + dense + RRF) | Robertson & Zaragoza 2009; Cormack et al. 2009 | Essential | `search.py`; benchmark in VALIDATION.md | Similarity is never treated as evidence |
| ANN indexes (HNSW, IVF), vector databases | Malkov & Yashunin 2018 | Unnecessary | Exact numpy search | Under 2k docs: exact search < 5 ms |
| Graph databases / GraphRAG | Edge et al. 2024 | Unnecessary | Typed edges in SQLite + Cytoscape | Corpus is small and the relations are explicit |
| Cross-encoder reranking | Nogueira & Cho 2019 | Experimental | Not used | Next step if retrieval quality matters more |
| Provenance (W3C PROV concepts) | W3C PROV-DM | Useful | Claims with source, method, grade, valid/recorded/access times, supersession | Simplified; not full PROV serialisation |
| Capability approach | Sen 1999 | Useful (normative) | "Open pathways" metric; optionality value model | Counts real options, not utility alone |
| Goodhart's law | Goodhart 1975 | Essential (warning) | Metrics shown separately; adversarial review targets metric gaming | Optimising the utility function is not optimising your life |
