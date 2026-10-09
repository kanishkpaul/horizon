# Recommendations (2026-10-09)

These come from simulated comparisons under explicit assumptions. They are not forecasts. Reference run: `RUN-20261009-181117-f49e`, 4,000 worlds, Balanced values, central scenario. All experiment outputs are in `research/experiments/`. Read [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md) before acting on any number.

## 1. The decision due this weekend: the register paper

The ARR October deadline is **12 Oct, 23:59 AoE** (13 Oct, 17:29 IST). The next cycle is **4 Jan 2027** (ACL 2027).

| Where the paper really is | Better choice in the model | Margin |
|---|---|---|
| About 25+ hours of work left, or confirmatory runs / human labels / κ not done | **January** | Clear (central: 9.91 vs 9.64) |
| 6–16 hours left but validation still incomplete | January, narrowly | Small |
| 6–16 hours left **and** validated | **October** | Small (9.97 vs 9.91) |

Your 27 September TODO listed open confirmatory runs, the oracle-v2 run, ~150 human labels including Prof. Naskar's κ pass, and cutting 11 pages to 8. On that evidence January looks right, but you know the current state and the model does not.

**If you submit in October:** a co-author with reviewing qualifications (Prof. Naskar, or the TUM collaborator if they have ≥3 qualifying papers) must file the ARR **service-contributor** form within 48 hours, i.e. by about 14 Oct AoE. Otherwise the paper goes into a lottery and may be desk-rejected. Undergraduates cannot fill this role. The original spreadsheet missed this rule.

**Either way:** tell your co-authors your decision by Saturday.

## 2. The policy that does best: a broad, sequenced portfolio

The strategy search found policies that beat every hand-designed preset by about 2 value points. They hold up in every model variant tested: adverse hours, no AI speed-up, outcomes independent, evidence having no causal effect, no relocation, and quality dilution. They are the minimax-regret choice under the Balanced, Robust, Research, Compensation and Optionality value models.

**What it is** (`disc_jan`; the outreach-first variant is `disc_jan_early`):
1. Faculty outreach plus a public MCW benchmark release early (Oct–Nov).
2. Register paper to the January ARR cycle, with a revise-and-resubmit fallback.
3. MCW written up → TMLR (rolling, judged on correctness) + arXiv.
4. SemEval-2027 system paper.
5. A Bengali register pilot built for MSR India, then predoc applications (~Feb).
6. PhD applications (Dec), only if a PhD interests you.
7. Targeted applications to Indian AI startups, big-tech and remote evaluation roles.
8. Collaborations from outreach replies; the Unify Continual-ARC baseline (via Daniel Lenton); an Epoch AI work sample; a small MVP; GPU/inference depth.
9. At most 4 things in parallel.

**Why it wins in the model:** it uses your available hours across the whole year (~1,200 h of career work, ~23 h/week on top of classes), where the presets leave capacity idle, and it does not burn the first week on an unlikely October push.

**The honest caveats:**
- It only makes sense if you will actually sustain ~60 hours of total work a week through semester 8. Under the adverse 50 h/week scenario it still ranks first.
- The model under-counts the costs of carrying many commitments: application quality, energy, reputational risk from weak applications. See the adversarial review.
- About half its value comes from items with **placeholder or judgment parameters** (offer odds, pay). The ranking is robust to swinging each of them; the absolute numbers are not meaningful.

**Among hand-designed strategies**, the Optionality barbell is the minimax-regret choice. Use it if you want fewer, deeper commitments.

## 3. What the model says not to do
- **Do not enter ARC Prize 2026 hoping to win the leaderboard.** ARC-AGI-3 is near saturation by frontier models (62.7–99.9% depending on harness). Virgil's value is as a cheap CPU-only baseline (the Unify route) or a paper-track note.
- **Conventional placement alone is dominated.** It has the lowest value under every value model.
- **The maximum-parallel portfolio** buys a little extra placement security (93%) at about 8 deadline-crunch weeks and fewer papers.
- **The founder track as the primary plan** only leads under the entrepreneurial value model, and even there only narrowly.

## 4. How your values change the answer (reference run, same simulated worlds)
The discovered portfolio ranks first under **all eight** value models. Among the hand-designed presets:

| Value model | Top presets | Infeasible (violates a hard constraint) |
|---|---|---|
| Balanced | Barbell, max-parallel, defer-depth | — |
| Research impact | Defer-depth, creation portfolio, research-first | — |
| Compensation | Max-parallel, research-engineering, barbell | — |
| Entrepreneurial | Max-parallel, founder, barbell | — |
| Optionality | Max-parallel, barbell, artifact-led | — |
| Autonomy | Defer-depth, creation portfolio, barbell | — |
| Robust (CVaR-20% + ≥80% position) | Max-parallel, barbell, artifact-led | defer-depth, research-first, founder, conventional |
| Bounded upside (p90 + position + crunch limits) | Barbell, creation portfolio, artifact-led | defer-depth, max-parallel, research-first, conventional |

## 5. Plan

All messages below are drafts for you to send; Horizon sends nothing.

**Next 24 hours**
- Decide October vs January (section 1). If October: line up the service-contributor registration today.
- Two-minute checks that remove model unknowns:
  - Can you post to arXiv in cs.CL without a new endorsement? (Start a submission to see.)
  - Is a full-time 8th-semester internship allowed at HIT? (One email to the department.)

**Next 72 hours**
- Write the first 3–5 faculty emails, each with one concrete, scoped proposal and a link to an artifact. Log the replies in the Cockpit, which recalibrates the reply-rate parameter. Targets: the first wave in Research → Outreach (e.g. Lingo Labs IITGN, which explicitly invites remote interns), plus the discovery hypotheses.
- Message Daniel Lenton: is Continual-ARC code coming, and would a zero-API Virgil baseline help? This uses an existing relationship.

**Next 7–14 days**
- Decide whether Daedalus/MCW becomes public. Two 2026 papers overlap; a public benchmark release stops the scoop clock and unlocks the Snorkel grant, EACL SRW and the Unify route.
- Optional, if they fit:
  - Predictive AI Evaluation Competition (30 Oct AoE). Strong fit for evaluation work; not in the model's portfolio, so treat it as unmodelled upside.
  - ELLIS PhD (31 Oct AoE), only if a European PhD interests you.

**Next 30 days**
- EACL 2027 SRW pre-submission mentorship draft (6 Nov).
- Founder/engineering-lead outreach with a working artifact.
- Start the MCW write-up.

**Next 90 days**
- PhD applications (~10 Dec, assumed), if relevant.
- FIRE 2026 in Kolkata (17–20 Dec).
- EACL SRW paper (15 Dec).
- January ARR submission (4 Jan).
- SemEval-2027 evaluation (10–31 Jan).

**Next 6 months**
- MSR India Research Fellow application (~mid-Feb, inferred), carrying the Bengali pilot as the targeted demonstration.
- MCW to TMLR.
- Startup and remote applications (Jan–May).
- Resubmit the register paper if needed.

The full dated list, with reasons, dependencies, success and failure criteria, and review dates, is in the **Cockpit** (generated from the reference run).

## 6. Created opportunities worth testing first

These are hypotheses about useful work you could offer, not vacancies. Ranked by plausibility × cost of testing.

| Target | Smallest demonstration | Cheapest test |
|---|---|---|
| Unify / Daniel Lenton | Virgil as a zero-API baseline on Continual-ARC | Ask whether the code is coming |
| Prof. Naskar + TUM collaborator | Turn the 56k-translation register data into a WMT27 challenge set or FIRE 2027 track | Raise it after the ARR decision |
| MSR India (multilingual group) | Bengali register-and-agents pilot | Read the group's recent papers; ask a current Research Fellow how they were selected |
| Epoch AI | One public benchmark review as a work sample | Check the role is open and India-eligible |
| Snorkel Open Benchmarks | A public MCW subset as a benchmark proposal | Check undergraduate eligibility |

## 7. What would change these recommendations
1. Your real remaining hours on the paper (section 1).
2. Your real sustainable weekly hours and the HIT academic calendar.
3. Whether you want a PhD, an industry research-engineering role, or a startup. Set this through a value model.
4. Real outreach reply rates (log them).
5. Citizenship and relocation, which unlock or remove several international routes.
