> Independent adversarial review by a separate worker (read-only; in-process experiments on a database copy), 2026-10-09. It is saved verbatim. The response and the fixes made afterwards are in the **Response** section at the end.

# Adversarial review: Project Horizon simulator and conclusions (2026-10-09)

## Verdict

Two of the four conclusions survive: "Optionality barbell is the minimax-regret preset" (robust under every stress I applied) and "Submit the register paper in January" (robust, but only as a statement about pre-Oct-12 capacity). Conclusion 1 does **not** survive as stated: the discovered portfolio (`disc_jan`) wins every single-factor stress I ran, but its ~2-point lead is driven by an assumed ~1,400 hours of pre-graduation project capacity and a utility that assigns zero value to unused time. Under plausibly harsher hours plus a modest value on time, barbell overtakes it, and with correlated applications `disc_jan` falls to 4th. Conclusion 4 (the VOI ranking) is an artifact of which strategies are compared: with `disc_jan` in the set every EVPPI is 0.

All runs below are in-process on a read-only copy of the DB (2,000–3,000 worlds, seed 4242 unless noted), paired with common random numbers. (`engine.py` gained an `evidence_shift_cap` patch during this review; it is inactive because the parameter is absent from the DB.)

## Findings

**1. High: `disc_jan`'s lead is mostly unbudgeted hours plus a utility with no value on time.**
Evidence: in the central scenario `disc_jan` uses 1,201 of 1,395 available pre-graduation project hours (86%); barbell uses 742 (53%). That is about 32 h/week of projects on top of classes for 9 months, with no rest, holidays or cumulative fatigue in the model (disruptions are about 2 weeks a year at 40%). The `disc_jan` − barbell gap is 1.95 in the central scenario, 1.85 at 45 h/week, and 0.54 ± 0.11 under "harsh hours" (the adverse preset plus heavier academics: 25/40/5/22/35 h). Under harsh hours plus 1 utility point per 800 h used, it is **−0.16 ± 0.11 (barbell wins)**. Add correlated batches (finding 2) and the ranking becomes barbell 4.93, `research_engineer` 4.75, `artifact_led` 4.72, `disc_jan` 4.55. Decomposition of the 1.95: count-type metrics contribute 0.98 (public outputs +0.41, already capped in 96% of `disc_jan` worlds; optionality +0.30; founder MVP +0.22; ties +0.05), fewer crunch weeks +0.42 (mostly from skipping October), peer review +0.25, and position by graduation only +0.05 (0.93 vs 0.90).
Fix: enter the real calendar; add an uncapped value-of-time term; add a combined-pessimistic scenario; re-run the search under the user's hours; report the lead as conditional on hours.

**2. High: application batches are modelled as independent tries.**
Evidence: each count outcome is Binomial(n, p), so 10 big-tech applications are 10 independent draws despite a shared résumé, CGPA screen and interview skill. Replacing n with an effective size n_eff = 1 + (n−1)(1−ρ) changes P(position by graduation) from 0.93/0.90/0.71 (`disc_jan`/barbell/conventional) to 0.84/0.82/0.52 at ρ = 0.5 and 0.75/0.76/0.34 at ρ = 0.8. At ρ = 0.8 no strategy meets the robust profile's 0.8 floor. The latent factors are too weak to supply this: the "independent outcomes" scenario moves scores by only about 0.03, while raising the loadings (portfolio 1.5, market 1.0, correlation 0.5) cuts `disc_jan`'s position probability from 0.93 to 0.84.
Fix: beta-binomial or a per-batch random effect with an explicit within-batch correlation; show position probability as a range.

**3. Medium: the "quality dilution" check has no effect.**
Evidence: the penalty only applies above 3 concurrently active actions; the average is 0.59–0.98 per week. As shipped it changes `disc_jan` by 0.00; at k = 1 and 0.3 per extra action, by −0.12. In fairness, a cumulative-breadth penalty (projects started beyond 8) hurts barbell *more*, because `disc_jan` front-loads its deadline-driven applications.
Fix: drop the "survives quality dilution" claim, or base the penalty on concurrent hours share or cumulative load.

**4. Medium: the VOI ranking depends on which strategies are compared.**
Evidence: on the current model (same seed, 4,000 worlds), with presets only, reply rate scores 0.068 and PhD admit 0.036, while Continual-ARC and TMLR score 0, so the stored ranks 3–4 do not reproduce. With `disc_jan` and `disc_oct` included, every EVPPI is 0. EVPPI also assumes perfect knowledge of a population reply rate; ten emails give a noisy estimate, so realistic EVSI is lower.
Fix: compute VOI against the recommended set; report EVSI for feasible information actions (10 emails, one department email).

**5. Medium: utility cap defaults reward breadth and can silently disable penalties.**
Evidence: any metric without an explicit cap gets cap 1.0, including negative-weight metrics. When I first added an hours penalty it saturated at 800 h, hiding the cost of `disc_jan`'s 1,245 h. Optionality (weight 1.5, cap 2, so up to 3 points) counts distinct offer *classes*, including non-position internships, and its ceiling exceeds that of position by graduation (2 points). Autonomy also counts research-internship offers.
Fix: require explicit caps and never cap negative-weight terms; count optionality over positions or down-weight it. Even with all count-type metrics removed, `disc_jan` still leads (5.26 vs 4.08).

**6. Medium (October vs January): October capacity and fallback priority bias the October case.**
Evidence: with 20 h of academics subtracted, the 3.5 days before Oct 12 give about 19 h against a central effort of about 42 h, so `reg_paper_arr_oct` completes in 9% of worlds. The Oct − Jan gap is −0.264 centrally, −0.14 with a 25 h four-day sprint, −0.06 for sprint + validated, −0.04 for near-done unvalidated, and +0.08 for near-done validated. Separately, contingent actions always get the lowest priority, so the January fallback in `disc_oct` is missed 8.3% of the time (0.9% in `disc_jan`). Fixing that priority raises peer-reviewed papers from 0.837 to 0.883, but the gap only moves to −0.235; most of the residual is the crunch penalty plus hours wasted on the failed attempt.
Fix: let rules set priority; model sprint capacity; carry partial October work into the January version.

**7. Low–Medium: evidence bonuses barely differentiate strategies.**
Evidence: the `public_outputs` token starts at 3, at or above the preprint (2) and artifact (1) caps, so those bonuses apply to every strategy from week 0. Setting the starting value to 0 leaves barbell unchanged and lowers `disc_jan` by 0.21; "evidence has no effect" is mostly a uniform level shift. A single generic `referrals` token raises the odds of every batch (big-tech, startup, remote, predoc), although real referrals are employer-specific; setting the referral bonus to 0 changes barbell by −0.30 and `disc_jan` by 0.00. Probabilities are frozen at submission, so later acceptances never help an interview (conservative).
Fix: tokens should count only *new* evidence; scope referrals per employer or batch.

**8. Low: policies know unknown facts for free.**
Evidence: initial tokens are copied from unknown parameters (`continual_arc_code`, `arxiv_endorsed`, `sem8_blocked`). The Unify action, and the creation-portfolio rule, know at week 0 whether the code will exist; in 40% of worlds the Unify action costs nothing.
Fix: hide these until an information action reveals them, and charge the hours of the attempt.

**9. Low: other engine issues.**
`_open` is not reset between `run()` calls, so results depend on run order (measured effect 0.0003). The critical-ratio scheduler pools remaining effort across worlds; this approximates expected effort, so it is not future leakage. No rule reads unobservable state beyond the tokens in finding 8. Strategies exceed `max_parallel` in 0.1% of worlds (negligible).

**10. Low: eligibility misclassifications.**
Evidence: the `GRADUATE_REQ` pattern `graduates? only` matches inside "Undergraduates only" (Innosprint 2.0 becomes eligible_later). "Recent graduates qualify" sends KAUST VSRP (which takes 3rd/4th-year undergraduates) to eligible_later. "Age 18+" pushes 12 opportunities into needs_check. Workbook "Not eligible…" maps to eligible_later rather than ineligible (Sasol, GEMS). AIXI's "level of a current PhD student" is read as PhD-only. None of this changes simulated numbers, because 0 `opp_` actions are shortlisted.
Fix: word boundaries, negation handling, treat "18+" as passed.

**11. Low: verified-claim supersession and ingest.**
Evidence: one strong agent claim supersedes *all* workbook claims on the same predicate. Nationality and general eligibility notes both map to `eligibility_text`, so a nationality claim hides unrelated degree or GPA notes. Agent-assigned grades are trusted automatically. Re-ingest is not idempotent: 10 of 14 annotated opportunities have duplicated `[verified]` segments, and field overwrites are not reverted.
Fix: supersede per sub-attribute; rebuild fields from claims rather than appending.

**12. Low: retrieval benchmark labels are noisy.**
Evidence: case-insensitive substring patterns over-match. `%ERA%` matches 33 accelerators ("accelERAtor") for the AI-safety query, `%ETH%` matches Ethereum and Netherlands entries, `%ARR%` matches WarriorHacks, and `%PhD%` matches non-European programmes. I estimate about 29% of the 150 labels are spurious. With 12 queries and no confidence intervals, the 0.004 nDCG gap between lexical and hybrid is noise, and name-pattern labels favour lexical search.
Fix: hand-labelled relevance sets with bootstrap CIs.

## What survives

- **Barbell is the minimax-regret preset.** It wins even under the combined stress and is second only to `disc_jan` under harsh hours plus correlated batches.
- **January unless near-done and validated.** Correct for the central effort estimate. The real threshold is whether you can finish *and* validate in about 20 focused hours (about 45 with a sprint).
- **Parts of the discovered portfolio are stable under every stress:** an unconditional MCW write-up with TMLR submission, early applications in deadline order, and no October crunch.
- **Search hygiene.** The final front is re-scored on fresh worlds (seed 8 vs 7), regret runs use another seed (4242), and CRN is used throughout. I found no number-changing bug larger than finding 6.

## What to tell the user

The 25-action portfolio wins mainly because the model assumes about 32 h/week of project work alongside classes, all year, and gives no value to time you don't spend. Enter your real timetable and exam weeks. Below about 50 h/week total, or if you value rest at all, barbell is as good or better. Treat "93% position by graduation" as an upper bound that assumes independent applications; about 75–85% is more realistic. Register paper: January, unless you can finish and validate it in about a day of focused work before Oct 12. The cheapest high-value learning is your own reply rate from the first 10 emails and the semester-8 internship policy; with the discovered portfolio included, no single unknown changes the recommendation.

---

## Response (fixes made after the review)

| # | Finding | Action taken | Effect |
|---|---|---|---|
| 1 | The lead depends on unbudgeted hours, and time has no value | **Value-of-time term** (`hours_used`, never capped) in every value model (−1 point per 800 h in Balanced); a combined **harsh** scenario in the robustness set; an **academic-load control** in the Lab; the strategy search re-run under central and harsh models | Broad-portfolio lead over barbell falls from 1.95 to 1.64 (central). Under adverse/harsh hours a *different*, leaner industry-first policy wins and becomes the robust-profile minimax choice. Recommendations are now conditional on hours |
| 2 | Application batches are independent | **Per-batch random effect** (`batch_logit_sd` ~ tri(0.5, 1.0, 1.6) logits) shared by every application in a batch | P(position) is still about 0.9 centrally because evidence and diversification across batch types remain. Documented as an upper bound; the harsh scenario raises the batch SD to 1.5 and the factor loadings |
| 3 | Quality dilution is inert | Claim removed from the docs; the variant is kept and labelled as concurrency-based only | — |
| 4 | VOI depends on the comparison set | VOI is now reported against the full set including discovered policies; EVSI is noted as future work | Every EVPPI is now 0: no single unknown parameter changes the top policy |
| 5 | Caps on negative weights; breadth-rewarding metrics | Negative-weight terms are never capped; explicit caps for every benefit; **optionality and autonomy count post-graduation positions only** (not internships) | Count-type advantage reduced |
| 6 | October capacity; fallback priority | **Rule-enabled actions jump to the front** of the non-urgent queue; a sprint scenario was added to the October/January analysis | Gap with a 25 h sprint is −0.16 (January still better); October wins only if nearly done and validated (+0.09) |
| 7 | Evidence tokens start saturated; generic referrals | `public_outputs` now counts **new** outputs only (starts at 0). Per-employer referrals are not yet implemented (documented) | — |
| 8 | Unknown facts known for free | The Unify action no longer requires the code token; if the code never appears, its hours are spent for nothing | — |
| 9 | `_open` not reset; RNG keys | Reset per run; stream keys stringified | Bit-identical reproducibility across run orders |
| 10 | Eligibility regex errors | Word boundaries; "undergraduates only" and "3rd/4th-year" no longer read as degree-required; "Not eligible" → ineligible; age rule narrowed; "level of a current PhD student" no longer read as PhD-only | Re-assessed |
| 11 | Ingest not idempotent | Previously appended `[verified]` segments are stripped before re-ingest | Per-sub-attribute supersession still to do |
| 12 | Noisy retrieval labels | Word-boundary regex labels; bootstrap 95% CIs | Hybrid nDCG@10 0.63 [0.48, 0.78], lexical 0.62 [0.49, 0.75], dense 0.54; differences are **not** significant. Hybrid has the best recall@10 (0.64) |

**Still open:** per-employer referral tokens; EVSI for realistic information actions; sprint capacity as a first-class choice; per-sub-attribute claim supersession; hand-labelled retrieval sets.
