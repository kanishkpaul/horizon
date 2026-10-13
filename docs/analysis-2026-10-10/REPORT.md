# Essential analysis of Horizon

10 October 2026. Personal decision-analysis project; evaluated on data integrity, simulation correctness and evidential strength. No implementation changes made.

## Conclusion

The project contains a functioning evidence catalogue and a meaningful framework for comparing alternative plans. **Its current strategy scores are provisional model outputs, not dependable personal outcome probabilities.** Several reproduced implementation errors affect the meaning of those outputs. The existing top-ranked plan has not been disproved, but its ranking needs recomputation after those errors are corrected.

## Essential checks run

- Backend tests: **30 passed**, using SQLite snapshots and temporary simulation archives.
- Frontend compilation/build: passed.
- Original data: **18/18 recorded SHA256 hashes match**.
- SQLite: integrity `ok`; no foreign-key violations.
- Catalogue: **570 opportunities, 3,605 claims, 824 sources**.
- Model: **71 parameters, 41 compiled actions, 13 strategies, 8 value profiles**.
- Real outcome/forecast evidence: **0 outcomes and 0 forecasts**.
- Historical reproducibility: **31 of 32 recorded runs lack their referenced world archives**. Summaries can survive without those arrays; the latest reference run does have its archive.

## Findings that matter to the analysis

| Finding | Evidence | Consequence |
|---|---|---|
| Pre-deadline time is overspent | Two 15-hour tasks both finish before a shared deadline allowing only 20 hours; simulator spends 30 | Tight concurrent deadlines can look feasible when they are not |
| Start dates do not correctly restrict capacity | A 30-hour task completes in a one-day window allowing about 5.71 hours | Short windows can receive too much work |
| “By graduation” includes a four-week grace period | Offer at week 3.5 counts when graduation is week 2 | The reported metric differs from its label |
| Risk ranking and comparison disagree | CVaR ranks constant 4 above a risky distribution, but “ahead by” reports −4 using means | The explanation and uncertainty statistic can describe a different decision criterion |
| Identical strategies produce an invalid comparison | Difference 0, SE 0, z infinity, marked resolved; JSON response fails | Ties are mishandled |
| Some profile edits do not reach simulation | Changing relocation to “no” leaves the model unchanged; scenario controls are separate | Corrected personal facts need not govern the recommendations |
| Model identity is incomplete | Changing weekly action capacity changes completion but leaves the fingerprint identical | Seed plus fingerprint does not guarantee historical replay |
| Robustness drops feasibility | Regret calculation takes raw scores without hard-constraint flags | It can recommend infeasible choices; the current probe's minimax choice was nevertheless feasible in all nine scenarios |
| A reply-to-project conversion parameter is unused | Leads directly enable collaboration actions; `p_reply_to_project` never applies | Outreach pathways omit a conversion gate; resulting optimism is plausible but its magnitude is unmeasured |
| Re-ingestion duplicates discovery relationships | Edges rise 1,752 → 1,893 → 2,034 on repeated ingestion | Graph counts are not stable under repeated import |

Two execution-layer issues also matter if the generated plans are used: an invalid calibration request commits the outcome/action completion before failing, and regenerating a plan duplicates completed actions while replacing unrelated generated todos. The daily scheduler respects capacity and due dates but not the simulator's prerequisite graph or contingent activation.

## What can be concluded scientifically

Most parameters are expert judgment, unknowns or placeholders: **47 expert, 7 placeholder, 7 unknown**, with 10 other provenance labels. There is no recorded prospective outcome sample to establish calibration. Small Monte Carlo errors show precise calculation under these assumptions; they do not show that the assumptions match this person's future.

Common random numbers, explicit prerequisites, adaptive policies and editable value models are useful analytical choices. Their conclusions remain conditional on the causal graph, priors, calendar and metric definitions. More simulation worlds cannot correct structural errors.

The current ranking therefore supports a hypothesis about which plans deserve comparison, not a validated assertion that a particular plan has a roughly 93% chance of securing a position. After correcting timing, input linkage and statistical semantics, the strategies should be rerun before interpreting their ordering.

## Retrieval check

The existing 12-query benchmark reproduces: nDCG@10 **0.620 lexical, 0.543 dense, 0.631 hybrid**; recall@10 **0.597, 0.544, 0.643**. Hybrid has the best point estimates, but this small regex-labeled benchmark does not establish a decisive superiority claim. It is a retrieval test, not validation of opportunity facts or the simulation.

External opportunity pages and deadlines were not refreshed. The audit does not certify every imported claim as current or correct.

## Evidence

The adjacent `probes.py` reproduces the targeted findings using disposable SQLite backups. `evidence.json` contains their outputs and the integrity/inventory checks. `retrieval.json` contains per-query results. `DETAILED_NOTES.md` retains the earlier broader audit notes; those include interface observations outside this essential analysis.

Production source and the original database were not edited. The temporary audit server has been stopped.
