# Validation

Run everything with `cd backend && uv run pytest -q` (30 tests, ~2 s).

## 1. Simulator against analytic answers (`tests/test_sim_validation.py`, 19 tests)

| Test | Known answer | Result |
|---|---|---|
| Deterministic plan | 50 h at 40 h/week completes at the end of week 1 | exact |
| Two-action Bayesian decision | E[A] = 0.3 × 10 = 3.0 vs E[B] = 2.5 | within 4 Monte Carlo SE |
| Resource constraint | Two 30 h tasks due in one week with 40 h: only the first in priority completes | exact, both orders |
| AND/OR reachability | AND needs both tokens; OR needs either | exact |
| Independent binomial batch | P(≥1 of 10 at p = 0.2) = 0.8926 | ±0.012 |
| Latent-factor correlation | loading 0 ⇒ P(both) = p²; loading 1.5 ⇒ P(both) > p² + 0.03 | passes |
| Information changes the decision | EVPPI = 2.0 exactly | 2.0 ± 0.3, decision-sensitive |
| Shortest path is not best | Short path (p 0.2) loses to long path (p 0.8) | passes |
| Two simultaneous prerequisites | 0.6 × 0.5 = 0.30 | ±0.015 |
| Hard constraint rejects higher value | Feasible lower-value option ranks first | passes |
| Reproducibility / common random numbers | Same seed ⇒ identical arrays; different seed differs; parameter draws shared | exact |
| Fractional-deadline week | Only the hours before the deadline count | exact |
| Contingent rule after a miss | Fallback action runs | exact |
| Monte Carlo error | SD of the mean shrinks ≥ 2.5× from n = 500 to 8000 | passes (theory: 4×) |
| Utility saturation and negative weights | Hand-computed | exact |
| Constraint statistics | p90 of 0..99 = 89.1 | exact |
| Derived metrics cannot be written by actions | Validator raises | passes |
| Resolve-time probability | A registration that lands after submission counts at decision time, not at submission | passes |
| Quality-dilution penalty | Many open commitments lower success odds | passes (note: in real strategies concurrency rarely exceeds 3, so this variant barely binds; see adversarial review #3) |

## 2. End-to-end acceptance (`tests/test_acceptance.py`, 11 tests, Part 28)

These run against a WAL-safe snapshot of the real database through the HTTP API:

- Import keeps all 163 original fields (1).
- Hybrid search and semantic neighbours, with the similarity caveat shown (2, 4).
- Graded evidence; superseded claims kept; hypotheses classified separately from vacancies (3, 23, 24).
- Relationship graph and AND/OR dependency map (5, 6).
- Editable value models (7).
- A shortlisted real opportunity becomes a simulator action (8).
- Simulation with assumptions, convergence and dominance; changed assumptions change results; re-ranking under other values (9–15).
- Theater spec traces to its run (16).
- Plan generation → outcome log → Beta calibration → undo (19, 20).
- Export and persistence (21, 22).
- Limitations stated (25).

**Video (17, 18)** is verified manually rather than in the suite, because it needs the server plus headless Chromium. A 129.5 s, 1280×720 H.264 + AAC MP4 with a WebVTT file was rendered from run `RUN-20261009-133034-fd0b`. Frames were extracted with ffmpeg at 2 s, 40 s and 100 s and inspected. Issues found and fixed from that inspection: footer overlap, duplicate offer labels, failures drawn as successes, too many lanes.

**UI (all workspaces)** was exercised in a headless browser (gstack browse): Brief, Atlas search + inspector, Lab what-if run (9 strategies × 3,000 worlds in 1.1 s), Tradeoffs, Uncertainty, Theater, Graph and unlock map, Cockpit plan generation. Zero application console errors. Screenshots are in `.gstack/browse-reports/`. Defects found and fixed: axis tick collisions, unreadable unlock-map layout, a misleading Pareto line (7-metric front drawn as a 2-D line), long titles, and `index.html` caching that served stale bundles.

## 3. Retrieval benchmark (`uv run horizon eval-search`)
12 queries. Relevance is defined by word-boundary regexes over names and organisations, written before looking at outputs (revised after adversarial review #12, which found ~29% spurious substring matches). 2,000-sample bootstrap CIs:

| Mode | nDCG@10 [95% CI] | Recall@10 |
|---|---|---|
| Lexical (FTS5 BM25) | 0.62 [0.49, 0.75] | 0.60 |
| Dense (bge-small-en-v1.5) | 0.54 [0.38, 0.71] | 0.54 |
| Hybrid (RRF, k = 60) | 0.63 [0.48, 0.78] | **0.64** |

The modes are **not** statistically distinguishable on nDCG with 12 queries. Hybrid has the best recall. Dense alone fails location and programme-name queries ("hackathon in Kolkata": 0.00; "PhD program in Europe": 0.00), and hybrid inherits part of that. Fusion weights were not tuned on these queries. Next steps: hand-labelled relevance sets, a location-aware boost, a cross-encoder reranker.

## 4. Convergence (every run)

Each run reports the batch-means standard error and the running mean for every strategy, and warns when the top two strategies are not separated (|z| < 2.5). At 3,000–4,000 worlds, utility SE ≈ 0.03 against strategy gaps of 0.1–2.0.

## 5. What is NOT validated

- **No out-of-sample test against real outcomes.** None exist yet. The forecast panel and outcome log are the mechanism; Brier scores become meaningful after about 20 resolved forecasts.
- **Expert-judgment parameters are untested** except through sensitivity and value-of-information analysis.
- **The created-opportunity hypotheses are untested.** Each has explicit invalidators.
