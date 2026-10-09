# Recommendations (2026-10-09, after adversarial review)

These are comparisons of policies under explicit assumptions, not forecasts.
- Reference run: `RUN-20261009-181957-7290` (4,000 worlds, Balanced values, central scenario).
- Robustness: 9 model variants, including a "harsh" variant (adverse effort, heavier academics, strongly correlated applications).
- Experiment files: `research/experiments/` (`regret_v2.json`, `search_v2.json`, `oct_vs_jan_v2.json`).
- The review that changed several conclusions: [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md).

## The short version

1. **Register paper: January (4 Jan, ACL 2027) unless it is nearly done *and* validated.** If you do submit on 12 Oct, a qualified co-author must file the ARR service-contributor form within 48 h.
2. **Do the shared core regardless of anything else.** Both winning policies (one for normal capacity, one for tight capacity) contain the same 17 actions. Front-load the cheap, informative ones: the public MCW benchmark, faculty and founder outreach, and the Unify message.
3. **Add the research-depth layer only if you can sustain ~60 h/week of total work and want a research or PhD path.** That layer is the MCW paper to TMLR, the MSR-targeted Bengali pilot, PhD applications, SemEval-2027 and GPU-systems depth.
4. **Your real weekly capacity and what you value decide between the two.** Set them in the Scenario lab (weekly hours, academic load) and with the value-model selector.

## 1. The register paper (due this weekend)

| State of the paper | Oct − Jan (value points) | Choose |
|---|---|---|
| About 32 h of work left (central estimate from the 27 Sep TODO) | −0.23 | January |
| You can sprint about 25 h before 12 Oct | −0.16 | January |
| 6–16 h left, validation incomplete | ±0.00 | Either; January is safer |
| 6–16 h left **and** confirmatory runs, labels and κ are done | +0.09 | October |

Why January wins unless the paper is near done:
- Only about 19 working hours remain before 13 Oct 17:29 IST once classes are counted.
- An unvalidated submission is penalised.
- A failed October attempt wastes hours and creates crunch.

Both paths keep a revise-and-resubmit fallback. Tell your co-authors your decision this weekend.

## 2. Which policy

| Value model | Least-regret choice across 9 model variants | Runner-up |
|---|---|---|
| Balanced | Broad portfolio (`disc_jan`), max regret 1.19 | Lean industry-first (`disc2_harsh`), 1.55 |
| Robust (CVaR-20%, ≥80% position floor) | **Lean industry-first**, 1.78 | Broad, 1.92 |
| Research impact | Opportunity-creation portfolio, 0.69 | Broad, 0.77 |
| Compensation | Research-engineering track, 0.45 | Lean industry-first, 0.49 |

Which policy is best in each scenario:
- **Broad portfolio:** central, no AI speed-up, evidence-has-no-effect, quality dilution, independent outcomes.
- **Its outreach-first variant:** aggressive hours, no relocation.
- **Lean industry-first:** adverse hours and the harsh variant.

| Reference run | Position by graduation | Peer-reviewed papers | Open pathways | Hours used | Crunch weeks | Median best pay (₹L) |
|---|---|---|---|---|---|---|
| Broad portfolio | 0.93 | 1.06 | 3.4 | 1,251 | 0.1 | 29.6 |
| Lean industry-first | 0.89 | 0.64 | 3.0 | 741 | 0.8 | 21.7 |
| Optionality barbell | 0.89 | 0.94 | 2.5 | 729 | 2.9 | 18.9 |
| Conventional placement | 0.68 | 0 | 0.8 | 147 | 0 | 14.6 |

**How to read this:**
- **Position by graduation is an upper bound.** Even with the new within-batch correlation, it assumes applications are less correlated than they may be. The review's ρ = 0.8 stress puts every strategy at about 0.75.
- **Pay figures are placeholders.** Read them only as relative.
- **The broad portfolio's lead is conditional on hours.** It wins because it uses about 1,250 hours across the year (about 32 h/week of projects through semester 8). At ~50 h/week total or heavier coursework, the lean policy is as good or better. Time now has a cost in every value model (−1 point per 800 h in Balanced; editable).

## 3. The shared core (both winning policies)

Ordered as I would do them; the Cockpit has dated items.
1. **Release a public MCW/Daedalus benchmark subset with harness and baselines.** It stops the scoop clock (two 2026 papers overlap), creates evidence for every application, and unlocks the Snorkel grant and EACL SRW. It is the one decision only you can make: is Daedalus going public?
2. **Faculty outreach, then founder and engineering-lead outreach.** Ten each, each with one scoped proposal and a link to an artifact. Log replies in the Cockpit; the reply-rate parameter recalibrates.
3. **Message Daniel Lenton** about the Continual-ARC code and a zero-API Virgil baseline. This is an existing relationship.
4. **Collaborations from replies** (up to 2 research, 2 industry).
5. **Applications:**
   - India predoc / MSR Research Fellow: about mid-Feb, inferred from past cycles; confirm in December.
   - Targeted Indian AI startups: Nov–Apr.
   - Big-tech: by Mar.
   - Remote evaluation roles: by May.
   - Epoch AI work sample: check the role is open and India-eligible first.
6. **Kolkata events, plus FIRE 2026** (Kolkata, 17–20 Dec).
7. **A small MVP from Blindfold or Maiku.** Low weight, kept because it adds a different kind of evidence.

## 4. The research-depth layer (broad policy only)
- MCW full paper → TMLR (rolling) + arXiv (check whether you need an endorsement).
- The Bengali register-and-agents pilot, aimed at MSR India's multilingual group, before the predoc application.
- PhD applications (~10 Dec), only if a PhD is a real option. In the model they matter little until the paper is accepted.
- SemEval-2027 (evaluation 10–31 Jan; one task includes Hindi).
- GPU/inference-systems depth.

## 5. What the model says not to do
- **Do not chase the ARC Prize leaderboard.** ARC-AGI-3 is near saturation by frontier models (62.7–99.9% depending on harness).
- **Do not rely on conventional placement alone.** It is last or near-last under every value model.
- **Avoid maximum parallelism.** It means about 8 crunch weeks for a few points of placement security.
- **The founder track as the primary plan** is not supported unless your values are strongly entrepreneurial.

## 6. Next steps (drafts only; Horizon sends nothing)

**24 hours**
- Make the October/January decision (section 1).
- Check whether you can post to arXiv in cs.CL without a new endorsement.
- Email the department about the 8th-semester internship policy.

**72 hours**
- Decide on Daedalus going public.
- Send the first 3–5 faculty emails. Lingo Labs (IIT Gandhinagar) explicitly invites remote interns.
- Message Daniel Lenton.
- Enter your real weekly hours and academic load in the Lab and re-run. This is the input that picks between the broad and lean policies.

**7–14 days**
- Benchmark release (aim for end of October).
- Founder outreach.
- Optional, unmodelled upside: Predictive AI Evaluation Competition (30 Oct AoE), which fits your evaluation work.
- ELLIS PhD (31 Oct AoE), only if a European PhD is a real option.

**30 days**
- EACL SRW mentorship draft (6 Nov), if MCW is going public.
- First collaboration projects.
- Startup applications open.

**90 days**
- FIRE (17–20 Dec).
- EACL SRW paper (15 Dec).
- January ARR (4 Jan).
- SemEval (10–31 Jan), broad layer only.

**6 months**
- Predoc/MSR application (~Feb).
- MCW to TMLR, broad layer only.
- Startup and remote hiring windows.
- Resubmission if needed.

## 7. What would change this
1. **Your sustainable weekly hours and real academic calendar.** These pick broad vs lean.
2. **What you value.** PhD and research vs industry pay vs founder upside; use the value model.
3. **The register paper's real state.** This decides October vs January.
4. **Logged reply rates from the first emails.**
5. **Citizenship and relocation.** These open or close international routes.

With the corrected model, no single unknown parameter changes the recommended policy (EVPPI is about 0 for the top set). The remaining uncertainty is about *you* (hours and values), not about the world's parameters.
