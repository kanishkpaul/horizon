# Audit of the original opportunity sheets

Inputs: `MASTER_AI_OPPORTUNITY_RADAR.xlsx` (research cutoff 2026-10-03) and `Kolkata_Online_Meetups_Oct2026_Jan2027.xlsx` (snapshot 2026-10-04), both built by Codex. Copies are stored read-only in `data/raw/` with SHA256 checksums. Every original field is preserved in `opportunity.raw_json`.

## Summary

The radar is a careful, high-recall **catalogue**. It is not a decision model: it has no probabilities, no quantitative values and no personalisation. About 20% of its rows matter for this person right now, and 14 of the options it lists are ones you cannot actually take.

| Finding | Evidence |
|---|---|
| 501 opportunities × 163 fields, 26 filtered views, 657-URL source registry, 333 organisations, 83 outreach targets, 192 search-gap notes | Workbook structure; every table imported |
| All 8 quantitative value columns (Money, Compute, Research, Career, Founder, Network, Distribution, Credibility value) are empty | Fill-rate profile: 0–1 non-empty cells each |
| All acceptance-rate fields are empty (Acceptance rate, Number selected, Number applicants) | 0 of 501 rows |
| The ranking it implies comes only from High/Medium/Low relevance labels. These are inflated: 323 rows are tagged "Researcher + Developer + Founder" and 432 "High" developer relevance | Field distributions |
| "Opportunity type" has 79 spellings for about 22 real categories | Normalised into `type_canonical` |
| Deadlines are calendar dates with a placeholder 12:00 time; only 107 rows carry an exact UTC instant (stored as Excel serial numbers); 286 rows have no deadline | Normalised with explicit precision labels |
| Deadline timezone field has 98 distinct free-text values | Parsed where possible; otherwise treated conservatively (00:00 IST on the date) |
| 25 deadlines passed between the cutoff (Oct 3) and today (Oct 9) | Eligibility engine marks them `deadline_passed` |
| Only 3 rows say "Eligible now"; 109 have no assessment | Sheet field |
| Undergraduate eligibility is stated for only 86 rows | Sheet field |
| Duplicate entry points: the Anthropic jobs page backs 12 rows, GovAI 6, UKRI 3 | Duplicate official URLs |
| 21% of rows are India-located; 81 US; ~130 "global/remote" | Country field |

## Verification against primary sources (2026-10-09)

The source-audit worker re-checked about 70 high-priority items. It produced 75 claims: 44 grade A, 19 B, 5 C, 7 D. 20 contradict the sheet; 11 sheet claims were superseded and kept as history.

**Wrong or stale in the sheet:**
- NAACL portal "not available" is stale; the ARR October cycle opened Sep 29.
- ELLIS PhD is marked UNKNOWN but is actually open (deadline Oct 31 AoE).
- Max Planck internships are listed as "rolling", but summer starts have a strict Nov 1 deadline.
- The OpenCV and IIT Mandi deadlines are each off by one day.
- The HackIndia AgentVerse link is dead.

**Listed as options, but you are ineligible:**
- Anthropic Fellows and Claude Corps: need US/UK/CA work authorization.
- DAAD RISE: North American, UK and Irish universities only.
- BlueDot grants: India is on their list of countries they cannot pay.
- Google Cloud AI Builder Cup: no students.
- NII internship, Mila, ETH AI Center doctoral: graduate students only.
- AAAI-27 student volunteer program: requires an AAAI-27 paper.

**Missed entirely:**
- The ARR **service-contributor rule** introduced this cycle. It decides whether the register paper is reviewed at all.

## Reconstructed methodology (what Codex did)

1. **What and why.** A worldwide radar for "AI/ML researchers, AI developers and startup founders", spanning money, compute, jobs, publication, education, mentorship, networks and government access. The aim was breadth (high recall), explicitly not proof of every opportunity.
2. **How.** A two-pass process: 317 rows reviewed on Oct 1, then 184 discoveries added. A 50-source hackathon inventory was built on Oct 3, and the 30 outreach targets came from first-party pages. Source hierarchy: official page → official announcement → portal → careers → first-party social → secondary.
3. **Opportunity types.** Every type a builder might want. Hackathons (88) and competitions (57) dominate; research internships (14) and research fellowships (11) are thin.
4. **Geography.** Worldwide, with an India slice. China and non-English ecosystems are acknowledged gaps.
5. **Eligibility.** Generic; not computed against a specific person. Most rows say "Potentially eligible".
6. **Verification.** Row-level labels (VERIFIED_CURRENT 251, PARTIAL 147, VERIFIED_HISTORICAL 67, COULD_NOT_VERIFY 36), with a "Verification scope" text per row.
7. **Recurring items.** 72 are historical or watchlist; recurrence is given as free text.
8. **Shared decision-makers.** Not modelled. For example, all 12 Anthropic rows share one hiring process.
9. **Selection biases.** Formal, advertised, English-language programs dominate. Evaluation-science employers, Indic venues, post-B.Tech research-entry programs and paid open-source work were under-sampled. Independent discovery found 50 such items not in the sheet.
10. **What would most change the results.** Personal eligibility facts (citizenship, relocation), base rates, and the person's own research assets as levers for creating opportunities.

## Meetup workbook

104 dated events (38 Kolkata, 66 online) plus 17 excluded leads. The list is broad: it includes social and non-technical events (salsa, board games), and many dates are single confirmed instances of a recurring series. It is imported as `event` rows. FIRE 2026 (Kolkata, Dec 17–20), found by discovery, is the most relevant research event in the window and was missing from this list.

## How Horizon fixes these

- **Temporal claims.** Each fact has a source, grade, valid time and access time; the history of superseded claims is kept (`claim` table).
- **Precision-labelled deadlines** (`deadline_quality`).
- **Rule-based eligibility against an editable profile**, with reasons shown for every status.
- **Access classes** (`verified_open`, `historically_open`, `evidence_supported_collaboration`, `speculative_hypothesis`, …) so a hypothesis is never presented as a vacancy.
- **Personal-strategy simulation** in place of relevance labels.
