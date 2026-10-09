# Major assumptions

Edit these in the app (Model & values) or in `data/seed/*.yaml`. Anything marked **(verify)** is a known unknown with value of information.

## About you (profile)
- **A-P1** Final-year B.Tech CSE at HIT Kolkata; graduation June 2027 *(CV, user-supplied)*.
- **A-P2** India-based; citizenship not recorded **(verify)**. Nationality-gated programs are marked "needs check", not ineligible, unless a verified restriction excludes India.
- **A-P3** Willingness to relocate is unknown **(verify)**. PhD applications abroad stay in the model; the "no relocation" variant removes them.
- **A-P4** Weekly work budget including classes: 50 / 60 / 72 hours (adverse / central / aggressive). The model never assumes reduced sleep.
- **A-P5** Academic load (placeholder): 20 h/week through 29 Nov; 35 during 30 Nov–20 Dec exams; 0 over the winter break; 14 in semester 8; 25 in the final weeks **(verify; replace with the HIT calendar)**.
- **A-P6** Existing relationships are only those evidenced in the CV ledger: Prof. Naskar, the TUM collaborator, Daniel Lenton, DisCo, PrettiFlow.
- **A-P7** Remaining effort on the register paper: 18–60 h, mode 32 **(verify; the most decision-relevant input)**. Based on the 2026-09-27 TODO; no commits since then.

## About the world (dated facts; see claims for sources)
- **A-W1** ARR October cycle: 12 Oct 2026 23:59 AoE; the service-contributor form is due 48 h later; feeds NAACL/COLING 2027 *(verified A)*.
- **A-W2** Next ARR cycle: 4 Jan 2027 AoE (ACL 2027 CFP) *(verified)*.
- **A-W3** ARC Prize 2026: code 2 Nov, paper 8 Nov *(verified date; time of day assumed)*. ARC-AGI-3 is near saturation by frontier models *(discovery)*.
- **A-W4** MSR India Research Fellow 2027 intake closes around mid-February 2027 *(inferred from past cycles, grade D)*.
- **A-W5** ICML 2027 deadline ~29 Jan 2027 *(assumed; page not published)*. US PhD deadline ~10 Dec *(assumed)*. Startup, big-tech, remote and research-intern application windows *(assumed)*.
- **A-W6** EACL 2027 SRW paper deadline 15 Dec *(discovery)*; FIRE 2026 Kolkata 17–20 Dec *(discovery)*; SemEval-2027 evaluation 10–31 Jan *(verified)*.

## Causal assumptions (evidence effects; logit shifts)
- **A-C1** A peer-reviewed paper raises research-selection odds: +0.5 ± 0.35.
- **A-C2** A preprint or public benchmark: +0.2 ± 0.2 (up to two count).
- **A-C3** A referral: +1.2 ± 0.5. The observational gap is ≈2.5 logits at one US firm, discounted for selection.
- **A-C4** A relevant artifact: +0.25 ± 0.2.
- **A-C5** Submitting before validation is complete: −0.5 ± 0.35.
- **A-C6** Being scooped before MCW is public: −0.8 ± 0.4. The scoop hazard is ~1.5%/week until public release.
- **A-C7** A targeted demonstration for a specific organisation: +0.35 ± 0.3.
- **A-C8** Shared latent factors make outcomes correlated (portfolio loading 0.5 ± 0.15; market 0.35 ± 0.1).

These are not identified from data. The **"evidence has no effect"** scenario sets A-C1 to A-C4 and A-C7 to zero; rankings among the top strategies are unchanged there.

## Execution assumptions
- **A-E1** Effort overruns: mean multiplier 1.4 (central); lognormal spread with geometric SD 1.5 (Buehler 1994; Flyvbjerg).
- **A-E2** AI assistance multiplies speed only on each action's automatable share: ×0.85 / ×1.25 / ×2.0 across adverse / central / aggressive (METR 2025 to Copilot RCT range).
- **A-E3** Output-equivalent hours: linear to 49 h/week, 0.4 marginal to 63 h, flat beyond (Pencavel 2014).
- **A-E4** Disruption weeks: ~4% chance per week; hours ×0.4.
- **A-E5** Switching cost: 4% of hours per concurrent action beyond 3. The quality-dilution variant also lowers outcome odds.

## Value assumptions
- **A-V1** No single objective is privileged. Eight value models are provided; all metrics are reported separately.
- **A-V2** Each metric saturates at a cap of 2–3× its reference value, so even "more outputs" stops counting after a point.
