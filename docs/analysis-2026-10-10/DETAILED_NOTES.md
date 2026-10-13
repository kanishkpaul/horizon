# Horizon: deep project analysis

**Audit date:** 10 October 2026, Asia/Kolkata. **Checkout:** `f184729`. **Scope:** architecture, application source, seed model, research artifacts and documentation, persisted database, tests, retrieval, frontend build, representative live UI behavior, and media metadata.

## Overall ruling

Horizon is a substantial working local decision workstation. It has a real evidence catalogue, executable probabilistic action graph, adaptive policies, multiple value models, retrieval, planning, outcome calibration, trace playback, and video artifacts. It is beyond a mockup.

**Its numerical recommendations are not yet reliable enough to guide consequential choices without inspecting the underlying assumptions and fixing the confirmed defects below.** Resource accounting can allow impossible deadline completions; “by graduation” includes four extra weeks; risk rankings are explained using a different statistic; some profile corrections do not affect simulation. These are implementation errors in addition to the acknowledged lack of empirical calibration.

The strongest current product is the evidence-and-assumption workbench. The weakest link is the transformation from personal facts and opportunity evidence into quantitative recommendations and then executable schedules. Adding more opportunities or Monte Carlo worlds will not repair that link.

This report distinguishes **reproduced** defects, **source-confirmed** behavior, and **inferences** about their impact. It does not claim the existing top-ranked strategy has been proven wrong. The correct ranking after repairs remains unknown.

## 1. What exists and how it fits together

| Layer | Implementation | Assessment |
|---|---|---|
| Original evidence | `data/raw/`, checksum manifest; workbook ingestion preserving `raw_json` | Good preservation boundary; all 18 listed raw hashes match |
| Catalogue and provenance | SQLite opportunities, claims, sources, organizations, people, hypotheses, research outputs | Rich schema and explicit origins; claim history and ingest idempotence need repair |
| Eligibility and relevance | Regex/rule assessment plus profile similarity | Explainable screening aid, not a complete eligibility engine; assessment timestamps become stale |
| Retrieval | FTS5 BM25 + local BGE embeddings + reciprocal-rank fusion | Appropriate for this corpus size; exact matrix search avoids unnecessary ANN infrastructure |
| Model compilation | YAML actions and parameters, shortlisted type templates | Inspectable and flexible; personal facts and eligibility are not fully connected |
| Simulation | Vectorized NumPy Monte Carlo, AND/OR conditions, staged outcomes, latent factors, common random numbers | Useful comparative machinery; timing and information semantics need stronger invariants |
| Decision analysis | Saturating utility, constraints, CVaR, pairwise comparisons, Pareto, EVPPI, sensitivity, regret | Broad coverage; several statistics and feasibility paths disagree |
| Strategy search | NSGA-II-style selection over action inclusion, ordering and parallelism | Useful exploration of the specified model; not evidence of global optimality or real-world validity |
| Execution | Generated action items, CP-SAT half-hour scheduling, outcomes, Beta updates, forecasts | Real implementation; destructive replacement, dependency omissions and transaction gaps limit trust |
| Explanation/media | Run traces → Theater specification → shared React frame → Chromium/ffmpeg, local narration | Good shared representation; a vivid simulated story can exceed the reliability of its model |
| Delivery | FastAPI, React 18/TypeScript, d3, Cytoscape; eight workspaces | Clear local architecture and restrained UI; request state, accessibility and narrow layouts need work |

The dependency direction is broadly sensible: originals → normalized catalogue → model → simulation/analysis → plans/explanations. However, there are multiple representations of the same facts: profile values, YAML initial tokens/calendar, opportunity assessments, simulation tokens, metrics, archived summaries, and current UI controls. Their synchronization is incomplete. This is the central architectural problem.

### Current persisted state

| Item | Count |
|---|---:|
| Opportunities | 570: 501 radar, 17 verification, 52 discovery |
| Claims / sources | 3,605 / 824 |
| Active / superseded claims | 3,594 / 11 |
| Organizations / people / events | 546 / 38 / 121 |
| Creation hypotheses / outreach targets | 18 / 83 |
| Parameters / strategies / value profiles | 71 / 13 / 8 |
| Compiled actions | 41 |
| Recorded runs / action items | 32 / 26 |
| Real outcome records / forecasts | **0 / 0** |
| Search documents, FTS and embeddings | 1,338 each |
| Relationship edges | 1,752 |
| Shortlisted opportunities | 0 |
| Media records with files present | 4 / 4 |

SQLite integrity check returns `ok`, with no foreign-key violations. The compiled model fingerprint is `aaaef8e76ebb`; the fingerprint itself is incomplete, as demonstrated below. All 570 eligibility assessments share a 9 October timestamp. Counts describe this local snapshot, not current external opportunity availability.

## 2. Confirmed defects, prioritized

Priority here means impact on this product: **P1** blocks trust in recommendations, records or execution; **P2** materially limits correctness/usability; **P3** is maintenance or polish. It does not imply every issue affects every current preset.

### P1 — Deadline capacity is not shared correctly

**Reproduced.** In `backend/horizon/sim/engine.py:403–445`, each action independently gets a fractional-deadline cap based on the original weekly capacity, while the remaining capacity tracks the whole week.

Two 15-hour tasks with the same halfway-through-week deadline and 40 available hours/week both complete. Only 20 hours exist before that deadline, but the engine spends 30. The existing fractional-deadline test covers one action and misses this interaction.

A separate reproduction gives a 30-hour task a one-day start-to-deadline window. The engine completes it using 30 hours when the available window contains approximately 5.71 hours. `start_week` is treated as a Boolean overlap, not a capacity fraction.

**Implication:** close deadlines and concurrent submissions can look feasible when they are not. Repair with shared sub-week capacity/event boundaries, then test multiple overlapping start/deadline windows, not only isolated actions.

### P1 — “Position by graduation” includes four extra weeks

**Reproduced.** `sim/engine.py:513` uses `offer_week <= graduation_week + 4`. A position arriving at week 3.5 is counted when graduation is week 2.

The UI and Theater repeatedly say “by graduation.” Either use the actual cutoff or expose a separately named grace-period metric. This is a semantic error even if it does not change a particular current strategy's result. An offer received also does not establish an accepted position or employment start date; those require distinct modeled events if the intended question is secure employment at graduation.

### P1 — Profile corrections do not reliably alter simulation

**Reproduced/source-confirmed.** `service.profile_facts()` supplies graduation, citizenship and relocation to assessment. `service.build_model()` loads YAML and parameter definitions, without connecting these facts to the curated model or scenario.

Changing `geography.relocation` to “no” leaves the compiled model unchanged. Profile graduation, academic load and exam edits are likewise not the authoritative simulation calendar. The scenario has separate relocation and academic controls; they can contradict the profile.

**Implication:** the user can correct an assumption and reasonably believe the recommendations incorporate it, while they do not. Establish one resolved configuration, show provenance for every resolved value, and explicitly distinguish notes from operative inputs.

### P1 — Risk rankings and their explanations use different statistics

**Reproduced.** `sim/analysis.py:91–115` ranks by the chosen risk measure but computes the top/runner-up difference, standard error and separation from mean utility.

For a safe strategy yielding 4 in every world and a risky strategy yielding 0 in 20% of worlds and 10 otherwise, CVaR at 20% correctly ranks safe first: 4 versus 0. The comparison nevertheless reports a difference of **−4**, because it compares means of 4 and 8. Brief then uses that number in its “ahead by” sentence (`views/Brief.tsx:89`).

Mean convergence is useful for mean utility; it is not automatically an uncertainty estimate for CVaR or a quantile. Use paired bootstrap or another justified estimator for the selected functional, and name any separately displayed mean difference.

### P1 — Exact ties are “resolved” and cannot be serialized through the API

**Reproduced.** Identical utility arrays produce difference 0, SE 0, `z = inf`, and `resolved = true`. FastAPI's JSON response rejects this with `Out of range float values are not JSON compliant: inf`.

`service._np()` has a nonfinite-float branch, but `json.dumps(default=...)` does not invoke the default handler for ordinary floats. Treat equality as a tie, represent undefined statistics safely, and enforce strict JSON on complete responses.

### P1 — Run identity and persisted replay are incomplete

**Reproduced/source-confirmed.** `sim/model.py:73–119` omits `max_hours_week` from action description/fingerprinting. It also omits model start, horizon, graduation, factor definitions and otherwise-outcome metrics from the fingerprint's full behavior specification.

Changing a 50-hour action's weekly cap from unrestricted to 1 hour leaves its fingerprint identical. One version completes in two weeks; the other never completes within the 20-week test horizon.

Run payloads store parameters, strategies and reduced action metadata, but not the complete compiled model or engine code identity. A seed and the current fingerprint cannot reconstruct arbitrary historical behavior after edits.

**31 of the 32 database run records point to missing NPZ world archives.** JSON summaries and traces can still exist; fresh reanalysis requires the missing arrays. The latest reference run has its archive, so the current Brief is not universally broken. Missing archives are explicitly handled by an existing recent commit, but the archive retention/export policy remains incomplete.

Persist canonical full model/configuration plus code/version identity. Back up the SQLite database and referenced archives/media together; a database-only export is not a complete project backup.

### P1 — Outcome logging is not atomic, and invalid parameters can be saved

**Reproduced.** `execution.py:156–194` commits the outcome and optional action completion before calibration validates the observation. Logging 6 successes from 5 trials raises an error but leaves one new outcome and marks the action done. Retrying can create another record.

Calibration rejects `successes > trials` and nonpositive trials, but does not enforce nonnegative successes or a valid update weight. `Dist.parse()` accepts `beta(-1,2)`, `normal(0,-1)`, `bernoulli(2)`, and `fixed(nan)`. Parsing a distribution's syntax is insufficient validation.

Validate the complete request before writing; commit outcome, status, parameter update and revision together. Add idempotency for retries. Validate distribution domains, finite values, request counts, and scenario/model references at the boundary.

### P1 — Feasibility is discarded in robustness and weakened in search

**Source-confirmed.** `analysis_jobs.py:46` copies every strategy's raw score into regret calculations, discarding `feasible`. `sim/analysis.py:144–153` then takes maxima over those scores. An infeasible strategy can become the benchmark or minimax choice despite hard constraints.

The current 1,000-world probe selects `disc2_harsh`, which is feasible in all nine scenarios. **This establishes a defect in the algorithm, not a demonstrated violation by that current recommendation.**

Search uses a fixed 10-point penalty on one axis for infeasible candidates; other axes can keep them nondominated (`strategy_search.py:134–145`). Final fresh evaluation exposes feasibility but score ordering alone is not a safe recommendation gate. Use explicit constrained dominance and a documented feasibility rule across scenarios.

### P1 — Plan regeneration can delete unrelated work and duplicate completed work

**Reproduced/source-confirmed.** `execution.generate_plan()` says it replaces the same run/strategy, but its deletion removes **all** `origin='plan' AND status='todo'` rows (`execution.py:103`). Doing/done rows survive, then fresh todo copies are generated. Completing one generated item and regenerating creates two copies of that modeled action.

Deletion and subsequent item creation are not one transaction. Generation also reads the **current** model while interpreting an **old** run; changed or removed shortlisted actions can mismatch historical results or fail after deletion.

Use stable identities keyed by run/strategy/action, scoped replacement, preserved progress, and the archived model. Stage and validate the entire plan before atomic replacement.

### P2 — Scheduling optimizes effort without the action graph

**Source-confirmed.** `schedule.py` respects daily capacity and due dates, but does not enforce prerequisite tokens, dependency order, action start dates, external reveals or contingent-rule activation. It schedules full `effort_hours` rather than measured remaining effort. Contingent actions enter the same todo pool as unconditional work.

Overdue actions are silently skipped rather than returned as unscheduled. The tasks-per-day setting is a penalty, not a hard limit. An “optimal” result means optimal for this reduced allocation problem; it does not establish an executable plan.

Retain the CP-SAT implementation, but make its constraint contract explicit and integrate readiness, precedence, remaining work and overdue reporting before presenting the result as a plan.

### P2 — Discovery ingestion adds duplicate edges on every run

**Reproduced.** Two calls to `research_ingest.ingest_discovery()` change edge counts **1,752 → 1,893 → 2,034**, adding the same 141 edges each time. Verification ingestion is idempotent in this probe.

Discovery replaces owned opportunities/claims but does not replace or deduplicate owned edges. Source insert-or-ignore also means changed source metadata need not update. Replacing imported claims is not the same as preserving an append-only evidence history.

Use deterministic IDs/unique keys and explicit ingest provenance. Test equality after repeated import and preserve changed assertions as revisions/supersessions.

### P2 — “Add to model” is broader than the compiler's actual support

**Source-confirmed.** `service.opportunity_actions()` supports only the available type templates. Unsupported types are silently omitted; the shortlist UI can still imply that they are modeled. Adding an action does not automatically select it in a preset strategy.

The compiler does not enforce assessed eligibility or access restrictions. It skips explicit past deadlines but can compile other blocked/closed opportunities. Generic type mapping can give a fellowship a predoc outcome or a job an Indian-startup outcome regardless of the opportunity's actual terms. Generic grant actions do not necessarily model the grant's financial value or requirements.

The nationality rule also treats a detected non-Indian restriction as blocking any known citizenship. A synthetic **US citizen / “US citizens only”** case returns ineligible. This is currently an India-profile heuristic rather than general editable citizenship logic.

Require an explicit compilation status, truthful modeled effects, applicability checks, and a strategy-selection step. Unsupported opportunities should remain inspectable without pretending they affect simulation.

### P2 — Outcome pathways omit a declared conversion gate

**Source-confirmed; impact direction inferred.** `p_reply_to_project` exists but is unused. Outreach produces lead tokens; collaboration actions consume a lead threshold directly and award collaboration/tie effects on completion. There is no separate modeled gate from a substantive reply to an agreed project using that parameter.

This can make outreach-centered pathways optimistic relative to a model with a real agreement gate. The magnitude and ranking effect require a counterfactual experiment; they are not established by this audit. `p_degree_on_time` is also unused.

Some metrics and causal tokens differ: an output metric is not consistently accompanied by the token that improves downstream applications. Define a canonical outcome event and derive reporting metrics and causal state from it.

### P2 — Frontend state can conceal mismatched or stale results

**Source-confirmed.** `lib/api.ts:21–37` retains previous data when a path becomes null or a changed request fails. Its request sequence protection is useful, but null paths do not invalidate an in-flight request. Some callers use separate effects without equivalent protection.

Brief catches a failed value-model reanalysis and falls back to old analysis under the new value-model label. Its information-value panel can retain the original objective's analysis. Lab controls initialize to central defaults rather than the displayed run's scenario; subsequent sensitivity/search operations can therefore use assumptions different from those shown in the run. Selected strategy state in Lab/Theater is not consistently reset when a different run changes the strategy set.

Theater render polling has no complete unmount/error cleanup. The provider's refresh does not uniformly invalidate all displayed resources. There is no application error boundary to contain a bad selection or response.

Use a query lifecycle keyed by run/configuration identity, clear loading/error distinctions, a visible stale/dirty state, and reset dependent selections when identity changes.

### P2 — Charts overstate or mislabel their mathematical meaning

**Source-confirmed.** `components/charts.tsx` computes its two-dimensional frontier assuming both coordinates should increase. Lab permits cost metrics such as hours/crunch without passing direction-aware transformations. The selected-metric frontier can therefore point the wrong way.

The statement that a mean-dominated strategy is “never the right choice under any weighting” is too broad for nonlinear saturation and risk-sensitive objectives. Mean dominance is not stochastic dominance. The convergence chart uses a weekly-axis component without providing sample-count tick formatting. Dot-range tooltips label the displayed point “mean” even when it is a risk score.

Carry metric direction, statistic and units as data, not label conventions. Qualify Pareto claims to the actual metric/statistic/objective class.

### P2 — Undo and concurrent writes are weaker than the product contract

**Source-confirmed.** Undo supports profile items, parameters, strategies and shortlist entries. Objective edits, action progress, outcome/forecast writes and strategy deletion do not all have equivalent revisions. Undoing calibration does not undo the outcome/action completion or reconcile every history record.

FastAPI shares one SQLite connection across synchronous thread-pool requests, using `check_same_thread=False` (`api.py:20–29`). The heavy-analysis lock does not serialize every write/transaction. Requests can interleave commits/rollbacks on the same connection. This is an architectural concurrency risk; no destructive race was induced in this audit.

Use request-scoped connections and explicit transaction boundaries. Either implement operation-level undo or narrow its promise to the operations it supports.

## 3. Scientific and decision validity

### What is well chosen

Common random numbers support lower-noise paired policy comparison. AND/OR prerequisites and adaptive fallbacks are more appropriate than treating opportunities as independent rows to rank. Explicit objective profiles distinguish values from probabilities. Saturation avoids unlimited value from repeated outputs. The system preserves unknown/placeholder origins and warns about assumed deadlines. The adversarial-review documents identify real weaknesses rather than hiding them.

These choices improve inspectability. They do not validate the parameter values or causal graph.

### What the present numbers mean

There are **zero real outcomes and zero forecasts** in the database. The parameters contain 47 expert-judgment, 7 placeholder, 7 unknown, 4 published-evidence, 4 scenario, 1 organizer-evidence and 1 historical-base-rate origins. Origin labels describe provenance, not individual predictive accuracy.

The current Brief reports roughly 93% simulated position success and 1.06 peer-reviewed papers for the January portfolio. Those are conditional outputs of this specified model. They are not calibrated estimates of this person's career chances, and the known graduation/timing semantics further complicate their interpretation.

A narrow Monte Carlo standard error answers “how precisely did we integrate this model?” It does not answer “how close is this model to reality?” More worlds reduce simulation noise, not structural bias, missing events or unjustified priors. Sensitivity across nine hand-picked variants is useful stress testing, not a confidence interval over all plausible world models.

The comparison also depends on compensation placeholders, transfer of population evidence to one individual, prior concentration, latent correlation and hand-specified artifact/referral effects. Even if money is only a proxy for relative rewards, its relative ordering and scale still matter to the value score.

### Information, time and search limitations

World state and the agent's known information need separate treatment. Hidden initial tokens can gate actions/probabilities even before the policy performs an information action; reveals often change what is displayed without fully governing action availability. An agent cannot choose based on a fact it has not observed.

Weekly stage resolution applies events before work allocation for the step, potentially making later-in-week information available to decisions at the beginning of that week. Immediate completion effects can similarly let successor actions use newly produced state without a fully consistent within-week chronology. Coarse weekly approximations are acceptable only when they preserve resource and knowledge constraints and are labeled honestly.

`effort_noise_gsd` is read from world 0 for every world (`engine.py:181`); the fixed current value hides this behavior, but an uncertain user edit would not work as intended. Inline parameter draws are keyed by distribution text, so distinct inline parameters with identical text can share a draw. Intended dependence should be explicit rather than an accidental consequence of string equality.

Single-parameter EVPPI evaluates perfect information for the existing strategy set and a mean-utility decision. It does not price all real research questions, joint information, newly enabled policies or the cost/time of obtaining evidence. Under CVaR, maximizing conditional means is not the same risk-sensitive decision problem. A zero result is therefore bounded by the estimator and candidate set.

Evolutionary strategy search finds policies that exploit the encoded model. It should be evaluated on fresh worlds, then challenged under repaired/alternative models. A discovered policy's high score is an incentive to inspect its causal shortcuts, not proof that it is a good real plan.

### Appropriate product boundary

Today Horizon is useful for collecting evidence, exposing missing facts, discussing tradeoffs, and generating hypotheses about sequencing. Numerical recommendations should be framed as provisional scenario comparisons. Before strengthening their status, require validated timing/knowledge invariants, traceable operative inputs, repaired feasibility, and prospective outcome evaluation.

## 4. Retrieval, provenance and freshness

The existing 12-query benchmark was rerun against the current read-only database and reproduced:

| Mode | nDCG@10 | 95% bootstrap interval | Recall@10 |
|---|---:|---|---:|
| Lexical | 0.620 | 0.485–0.754 | 0.597 |
| Dense | 0.543 | 0.377–0.709 | 0.544 |
| Hybrid | 0.631 | 0.479–0.778 | 0.643 |

Hybrid has the best point estimates here; its nDCG advantage over lexical is small. Overlapping intervals alone are not a paired significance test, and this benchmark does not establish a decisive superiority claim. Dense returns zero relevance on the benchmark's Kolkata and European PhD queries. Hybrid retains weaknesses on those queries.

The relevance sets are generated from name/organization regexes, not independent graded human judgments over complete opportunity requirements. This can count superficial matches and miss relevant synonyms. Use held-out hand judgments, eligibility-aware cases and query-level error analysis before tuning reranking.

Preserving 163 original fields in `raw_json` is a strong archival feature. However, preservation is not canonical truth resolution. Per-attribute supersession, contradictory source handling and freshness remain incomplete. Grades carried from a workbook or research worker require assertion-level evidence checks before being treated as verified.

The assessment cache does not automatically age as deadlines pass. Model/template compilation and Atlas can then disagree about applicability. Refresh date-dependent assessment on a defined lifecycle and surface the assessment time. External program pages, rates and deadlines were **not refreshed on the web in this audit**; no volatile research claim is certified current here.

## 5. Interface audit

The Newsreader/Instrument Sans/JetBrains Mono typography, quiet colors, chronology ruler and consistent workspaces give the product a coherent identity. The Brief makes a concrete recommendation and places caveats nearby. Evidence inspection and editable origins are unusually useful. Avoid spending the next iteration on decorative redesign; trust and interaction correctness have higher value.

Representative live navigation covered all eight workspaces against a disposable SQLite snapshot. The desktop Brief and Lab rendered, and no warning/error console entries were captured in that navigation pass. This was not an exhaustive interaction or assistive-technology test.

At a **390 × 844 viewport**, the Lab's fixed minimum control column leaves the results squeezed into a nearly unusable sliver. The page need not have a large document scroll width for this to be a layout failure. Similar fixed columns exist in Theater and Research. The default narrow desktop/browser viewport also truncates Lab tabs and long content.

### Impeccable audit ratings

These are qualitative review ratings, **0 = severely deficient, 4 = strong**, not standardized accessibility certification.

| Area | Rating | Evidence and required next step |
|---|---:|---|
| Accessibility | 1/4 | Clickable rows, graph and chart details lack equivalent keyboard access; modal focus management/semantics and tab state need repair |
| Performance | 2/4 | Fast local computation and appropriate dense retrieval; main JS is 840 kB / 269 kB gzip; route code splitting and bounded long jobs are absent |
| Theming | 3/4 | Shared semantic variables, coherent light/dark styling; contrast and every chart state still need measured QA |
| Responsive behavior | 1/4 | Live narrow Lab failure; fixed multi-column Theater/Research; hidden rail controls and horizontally crowded tabs |
| Interface integrity | 2/4 | Strong provenance/caveats, but stale analysis labels, incomplete undo, “by graduation” semantics and compiler promises compromise trust |

Concrete accessibility work: make row actions actual controls/links; provide a text/table alternative for graphs and mouse-only tooltips; implement dialog labeling, focus trap, initial focus and focus restoration; use correct tab roles/selected state and keyboard navigation; label editable inputs. Visible focus styling already exists and should be retained. Contrast, reduced motion and a full screen-reader journey were not certified.

The Impeccable detector flagged the small neutral note-border treatment as a possible side-tab pattern. Inspection suggests a functional note indicator, so it is not counted as a material defect.

## 6. Verification and engineering quality

**Verified during this audit:**

- Backend suite: **30 passed**, using the real acceptance fixture's SQLite snapshot and redirecting generated archives to a temporary root.
- Frontend: `npm run build` passed TypeScript and Vite. Build emits a large main chunk; no frontend test script exists in `package.json`.
- All **18** raw checksum entries match.
- SQLite integrity and foreign keys pass.
- Targeted probes reproduce the defects listed above in temporary snapshots; originals are opened read-only.
- Current retrieval metrics reproduce the documented benchmark.
- Four existing explainer MP4s are present and ffprobe reports H.264 video at 1280×720 plus AAC audio, with durations 104.33, 111.08 and 129.5 seconds (two at 129.5).

Media metadata is not proof of correct audio, pacing, captions or end-to-end playback. No new video was rendered and the full videos were not listened to. Existing documentation records earlier frame inspection; that is historical evidence, not a newly repeated check.

The 19 analytic simulator tests cover valuable primitives: resource choice, prerequisites, batch success, latent correlation, adaptive fallback, deterministic replay and utility. The 11 acceptance tests cover the happy-path product integration. Passing them is meaningful, but the failures above show the suite does not yet enforce multi-action fractional timing, full fingerprint identity, risk-consistent comparisons, invalid-input atomicity, repeated plan/import behavior or dependency-aware schedules. Search quality tests also cannot validate the research model.

The repository has a backend lockfile and frontend lockfile, straightforward module boundaries and useful docs. Risks are concentrated in the broad service/API orchestration, dictionary-shaped request schemas, multiple sources of truth, and insufficient operation-level invariants. A microservice rewrite is unnecessary. Typed contracts, canonical configuration, transaction discipline and focused invariant tests would provide more value.

The local server defaults to loopback and does not implement outbound messaging/application submission. A dedicated security penetration review was not performed. For ordinary reliability, request bounds, path containment, error handling and shared-connection isolation still warrant hardening before any broader hosting.

### Documentation drift

`MODEL_CARD` describes 69 parameters and progress text mentions 72; the actual registry has 71. The methodology registry's CP-SAT status lags the implemented scheduler. The UI says “Run 7 scenarios,” while the comparison currently runs nine. Some recommendation documents reference runs whose world archives are absent. Old paths and historical benchmark figures should be labeled by date/version rather than left as current operational instructions.

Retain the adversarial review and decisions history. Generate machine-verifiable inventory/model details from the same resolved configuration used for execution, and make recommendations link to a retained run bundle.

## 7. Recommended repair sequence and acceptance gates

### Gate A: preserve records and make inputs operative

1. Snapshot the complete database/archive/media bundle and make missing references visible.
2. Validate distributions and request schemas; make outcome/calibration and plan replacement atomic and retry-safe.
3. Implement stable scoped plan identities and idempotent research ingestion.
4. Resolve profile, scenario, eligibility and model facts into one auditable configuration.

**Pass condition:** rejected input leaves zero changes; repeating an operation creates no duplicates; unrelated and completed actions survive regeneration; correcting relocation/graduation changes the actual resolved simulation inputs.

### Gate B: repair the simulator and decision semantics

1. Enforce shared within-week capacity, start windows and causal event ordering.
2. Separate latent state from observed information; audit every information-action gate.
3. Correct graduation cutoff and define offer/accepted/start metrics distinctly.
4. Fingerprint and archive every behavior-affecting field with engine identity.
5. Make comparisons, uncertainty estimates, Pareto direction and EVPPI consistent with the selected objective.
6. Preserve hard feasibility through regret and search.

**Pass condition:** analytic multi-task/window fixtures conserve capacity; policies cannot use unrevealed facts; exact ties are serializable and unresolved; equivalent complete configurations replay, and every behavior-changing edit changes identity; infeasible options cannot be recommended.

### Gate C: make the product's visible claims match its behavior

1. Label unsupported shortlist entries and stale/dirty analysis explicitly.
2. Synchronize UI selections with run/configuration identity and handle failures without old-result substitution.
3. Make CP-SAT schedules readiness/dependency-aware and report overdue work.
4. Repair narrow layouts and keyboard/modal/graph access.
5. Add a small number of real browser journeys for edit → recompute → inspect → plan → outcome → undo.

**Pass condition:** every displayed recommendation names the exact input/run/objective it uses; a 390px viewport remains usable; the core journey works with a keyboard; old run plans use their archived model.

### Gate D: evaluate the model prospectively

Log forecasts and actual outcomes with dates, denominators and the precise parameter/path they inform. Predeclare evaluation questions and avoid treating selected successes as a random sample. Challenge reply-to-project conversion, output-quality thresholds, time estimates, offer timing and cross-outcome dependence. Report calibration/forecast scores with small-sample uncertainty and preserve failed predictions.

Use independent held-out relevance judgments for retrieval. Re-evaluate current strategies after correctness repairs before adding search sophistication. Any claim about real-world superiority should have evidence separate from passing software tests and agent-authored audits.

## 8. Audit artifacts and reproducibility

- `evidence.json`: snapshot counts, raw/archive checks and individual reproduction outputs.
- `probes.py`: rerunnable targeted reproductions; original database read-only, mutations only in temporary SQLite backups.
- `retrieval.json`: full current benchmark with per-query results.
- `media.json`: current ffprobe stream/duration checks.

Run the probes from the project root:

```sh
backend/.venv/bin/python docs/analysis-2026-10-10/probes.py
```

The acceptance suite was run with generated archives redirected as follows:

```sh
backend/.venv/bin/python -c 'import pytest; import horizon.service as s; from pathlib import Path; import tempfile; s.ROOT=Path(tempfile.mkdtemp(prefix="horizon-audit-tests-")); s.RUNS=s.ROOT/"runs"; raise SystemExit(pytest.main(["backend/tests", "-q", "-p", "no:cacheprovider"]))'
```

The analysis reviewed application modules, configuration, tests, docs and representative persisted artifacts. It did not independently verify every one of 3,605 claims, externally refresh every opportunity, visually inspect all original CV/workbook pages, certify security/accessibility, or empirically validate personal outcome probabilities. Those are distinct tasks with distinct evidence requirements.

No production source fixes, commits, external messages or applications were made. The substantive new files are this audit folder. The frontend build regenerates ignored build output; simulator and UI mutation probes use disposable database copies and temporary archive paths.
