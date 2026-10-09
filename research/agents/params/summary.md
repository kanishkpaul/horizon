# Empirical parameters: summary (accessed 2026-10-09)

80 parameters are in `parameters.jsonl`. Grades: 39 A, 13 B, 16 C, 12 D. 20 have no point estimate and must stay as scenarios. The web-search budget ran out before every item was covered (job-search funnel reports, workshop-level counts).

## Solid evidence (grade A, published by organizers or studies)
- **Venue base rates.** ACL 2025: 20.3% main, 16.7% Findings. NAACL 2025: ~22% / 15%. NeurIPS 2025: 24.5%. ICLR 2026: 27.4%. TMLR 2025: 70.6% of reviewed papers (46.3% of all submissions), median 104 days to decision.
- **Program funnels.** GSoC 2026: 1,141 of 15,245 applicants (7.5%). YC W24: under 1%. SIH 2025: 2.0% of teams reached the finale, and about 20% of finalists won.
- **Referrals.** In one US firm (Brown, Setren & Topa 2016), referred applicants were interviewed ~5x as often as job-board applicants (10.2% vs 1.9%) and got offers ~11x as often (3.1% vs 0.27%).
- **Internships.** NACE: 62–63% of US interns get or convert to a full-time offer.
- **Faculty email audits.** US faculty answered 67% of meeting requests from prospective PhD students; Australian faculty answered 43% within 24 h. Both show a penalty for South Asian names.
- **AI productivity RCTs.** Peng 2023, Brynjolfsson 2025, Dell'Acqua 2023, Cui 2025 and METR 2025.
- **Human performance.** Van Dongen 2003 (sleep restriction), Buehler 1994 (people took 1.64x their own estimate; only 30% finished on time), Heathcote 2000 (exponential practice curves), Cepeda 2006/2008 (spacing).
- **Compute.** Hugging Face ZeroGPU docs.

## Effectively unknown (keep as scenarios)
- Acceptance rates for MSR India Research Fellows, Google Student Researcher, the Anthropic Fellows (only outcomes are published), OpenAI Residency, LFX and Entrepreneur First.
- Workshop paper acceptance and arXiv moderation decline rates.
- Cold-email reply rates for an Indian undergraduate writing to foreign faculty, founders or recruiters. The audit studies are upper bounds for a cheaper request.
- Hackathon placement odds outside SIH, and the cost of switching between multi-day projects.
- India stipends and salaries: only vendor or self-reported ranges exist (grade C/D).

## Biggest warnings for the simulator
1. **AI speedups.** Vendor and greenfield studies report +26% to +56%. METR's RCT found experienced developers were 19% *slower* while believing they were 20% faster. METR's 2026 follow-up is inconclusive (CIs span zero, heavy selection). Dell'Acqua found AI *lowered* correctness by 19 pp on tasks beyond the model's frontier. No RCT covers a solo researcher using agentic tools. Apply only a modest, wide multiplier to coding subtasks. Do not apply it to research judgment. Add a silent-error and rework term.
2. **Self-estimates are biased.** Planning-fallacy and METR data both show that self-reports are optimistic. Calibrate duration and speedup parameters from the person's own logged history, not intuition. Use heavy-tailed overrun distributions (Flyvbjerg: power-law tails).
3. **Population rates are not this person's rates.** ACL 2026 acceptance (main or Findings) was 39% for papers with a reviewer-qualified author, 25% for "outsider" papers and 10% for all-student outsider papers. The co-authored Indic MT paper and a solo Daedalus paper belong in different bins. These figures come from a secondary report of the program chair's analysis (grade C until the original is read).
4. **Rates are moving fast.** EMNLP 2026's main-track rate fell to about 15% as submissions doubled. arXiv now limits authors to 2 submissions a month, and since January 2026 a new author needs a peer endorsement. Re-pull these numbers each cycle.
5. **Correction to the profile.** ZeroGPU now runs on RTX Pro 6000 Blackwell GPUs, not H200. Pro accounts get 40 min/day at the half-GPU (48 GB) size, or 20 min/day at the full 96 GB size, which bills at 2x. That suits demos, not batch evaluation runs.
6. **Weak ties have small per-tie value.** In Rajkumar et al. 2022, a single new tie produced a job with probability on the order of 0.1%. Model networking as many draws, not as a few decisive contacts.
