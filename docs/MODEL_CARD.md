# Model card: horizon-sim 0.3

## What it is
A vectorised discrete-time Monte Carlo simulator of one person's actions over 52 weeks (from 2026-10-09). Each simulated world:

1. **Draws uncertain parameters** from the registry (`data/seed/parameters.yaml`; 69 parameters, each tagged with its origin).
2. **Draws latent factors:** `portfolio` (how evaluators judge the person's record) and `market` (hiring conditions), correlated at 0.2.
3. **Runs a policy week by week:**
   - external responses resolve;
   - exogenous hazards fire (being scooped; the Epoch role being filled);
   - policy rules enable or disable actions;
   - hours are allocated (weekly budget, minus the academic calendar, minus disruptions; output concave above 49 h/week; switching cost beyond 3 concurrent actions);
   - actions complete and schedule their outcome stages; missed deadlines are recorded.
4. **Reports metrics in natural units:**
   - peer-reviewed and workshop papers, new public outputs;
   - best secured pay; position by graduation (June 2027) and by horizon;
   - open pathways (distinct offer classes plus new collaborations plus founder traction);
   - research autonomy (0–3), founder stage, new ties, external uptake, prizes and grants;
   - deadline-crunch weeks, hours used.

Outcome probabilities are `sigmoid(logit(base) + evidence shifts + factor loadings)`. Base rates and shifts are parameters. Shifts are causal *assumptions*: their uncertainty includes zero, and the "evidence has no effect" variant switches them off.

## Intended use
Comparing adaptive policies under explicit, editable assumptions; finding which unknowns matter (value of information); testing robustness across model variants; turning a chosen policy into dated actions; and learning from logged outcomes.

## Not intended for
Predicting what will happen to you. Assigning a number to your worth. Replacing judgement about what you value. Ranking real people or organisations.

## Inputs and their quality (origins)
- **published_empirical / organizer_published:** venue acceptance rates (ACL/NAACL 2025), YC acceptance, TMLR timing, ARR timing.
- **expert_judgment:** most selection probabilities and all evidence effects. Each cites the nearest evidence and states why it may not transfer.
- **unknown:** predoc acceptance, founder reply rates, Epoch offer odds, Emergent Ventures odds, arXiv endorsement status, 8th-semester policy, Continual-ARC code release.
- **illustrative_placeholder:** compensation levels, grant and prize sizes. Never read pay outputs as estimates.

## Validation
See [VALIDATION.md](VALIDATION.md): 19 tests against analytic answers, convergence diagnostics in every run, a retrieval benchmark, and an adversarial review.

## Known limitations
1. **The action catalogue is the boundary of the model.** Opportunities nobody wrote down cannot appear; created opportunities enter only through 8 curated hypothesis actions plus generic outreach.
2. **Breadth is cheap in the model.** Beyond hours, switching costs and a concurrency-based quality-dilution variant, the costs of carrying many commitments over a year are not modelled: fatigue, reduced quality per item, reputation risk from weak applications. Strategy search exploits this.
3. **The academic calendar is a placeholder** (20 h/week in semester, 35 in exams, 14 in semester 8).
4. **Effort estimates are mine, not yours.** The October-paper decision depends almost entirely on your own remaining-hours estimate.
5. **Offers are binary per class**, and compensation is one draw per class per world.
6. **Batch applications use one shared probability**; heterogeneity between programs within a batch is ignored.
7. **No acceptance or rejection decisions.** Holding several offers counts as optionality; real deadlines for accepting offers are not modelled.
8. **Weekly granularity.** Same-week ordering of events is approximate.
9. **The utility function rewards outputs up to saturation caps**, so quantity is partly rewarded regardless of quality.

## Reproducibility
Every run stores: seed, model fingerprint (hash of actions, parameters, offer classes and exogenous events), dataset version (hash of the source workbooks), scenario, value model, parameter distributions, warnings, limitations, and world-level metric arrays (`data/runs/<id>.npz`). The same seed and fingerprint reproduce identical results (tested).
