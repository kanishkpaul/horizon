# Progress

## State on 2026-10-09 (end of session 1)

### Working and verified
- **Data.** 570 opportunities (501 radar + 17 verification + 52 discovery), about 3.6k graded temporal claims (11 superseded), 824 sources, 546 organisations, 121 events, 83 outreach targets, 18 creation hypotheses.
- **Eligibility.** Rule-based against the editable profile, with reasons; verified blocks from primary sources.
- **Hybrid search.** Benchmark: hybrid recall@10 0.56; lexical nDCG 0.61, about equal to hybrid.
- **Simulator.** 41 actions, 72 parameters with origins, 2 exogenous hazards, adaptive rules, saturating evidence effects, quality-dilution variant.
- **Analysis.** Value models with hard constraints and risk measures, paired dominance, Pareto, EVPPI, regret across 8 model variants, tornado, NSGA-II search over action sets *and* order.
- **Execution.** Plans across 24h–12m horizons; outcome logging with power-prior calibration; forecasts with Brier scores; undo.
- **Interface.** 8 workspaces, verified in a headless browser with no app errors.
- **Video.** The theater renders to MP4 (H.264 + AAC narration via macOS `say`) with WebVTT captions, from the same React frame. Two renders checked frame by frame.
- **Tests.** 30 passing (19 analytic validation, 11 end-to-end acceptance).
- **Docs.** AUDIT, METHODOLOGY_REGISTRY, MODEL_CARD, ASSUMPTIONS, VALIDATION, DECISIONS, RESEARCH_LEDGER, RECOMMENDATIONS, ADVERSARIAL_REVIEW.

### Model changes after self-review and adversarial review (model 0.3.1)
See the Response table in ADVERSARIAL_REVIEW.md. Highlights:
- Value of time in every value model.
- Per-batch application correlation.
- Saturating, new-only evidence.
- High-priority fallbacks.
- Positions-only optionality.
- Harsh scenario and an academic-load control.
- Eligibility regex fixes; idempotent ingest; regex-labelled retrieval benchmark with confidence intervals.
- A CP-SAT 14-day scheduler in the Cockpit.

### Earlier self-review changes
1. A revise-and-resubmit action, and an adjustable rushed-paper penalty. The original model was biased toward deferral.
2. Evidence shifts saturate (`evidence_shift_cap`). Stacked bonuses had raised per-application predoc odds from 7.5% to 45%; now about 19%.
3. Strategy search evolves priority order, not just inclusion.
4. A quality-dilution scenario (breadth penalty).

### Next
1. Open review items: per-employer referral tokens; EVSI for realistic information actions; sprint capacity as a choice; per-sub-attribute claim supersession; hand-labelled retrieval sets.
2. Replace the placeholder academic calendar and the profile unknowns with your real answers; log the first outreach outcomes.
3. Feed the CP-SAT scheduler from calendar availability (it currently uses weekday/weekend hours).
4. Regression-based EVPPI; hierarchical pooling once there are ~30 logged outcomes.
5. Per-program heterogeneity inside application batches; offer-acceptance decisions.
6. Retrieval: location-aware boost or cross-encoder reranking.
7. A Remotion/Manim path for concept explainers (not needed for trajectory videos).
