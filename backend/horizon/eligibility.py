"""Rule-based eligibility assessment against the editable personal profile.

Output statuses, in decreasing order of actionability:
  eligible_likely      no rule found a blocker and the source says undergrads/internationals are fine
  needs_check          a fact that decides eligibility is unknown (citizenship, age, group, wording)
  eligible_later       requires a completed degree or later career stage
  travel_or_relocation in-person abroad; feasible only if travel/relocation is acceptable
  ineligible           an explicit rule excludes this profile
  deadline_passed      the recorded deadline is in the past and no next cycle is known
  closed_watch         closed but recurring; watch for the next cycle

Every status carries the list of rules that fired, so the user can disagree with a specific rule.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .normalize import is_global, is_india

NATIONALITY_BLOCK = re.compile(
    r"\b(u\.?s\.?|united states|american|eu|european union|uk|british|canadian|australian|new zealand|"
    r"south african?|kenyan|nigerian|african|singapore|swiss|german|french|japanese|korean|chinese|"
    r"taiwanese|israeli|kurdistan|iraq|uae|emirati|saudi)\s+(citizens?|nationals?|residents?|permanent residents?)",
    re.I,
)
PHD_ONLY = re.compile(r"(phd|doctoral)\s+(students?|candidates?)\s+(only|enrolled)|must be (enrolled in|pursuing) a (phd|doctoral)"
                      r"|current(ly)? (enrolled )?(phd|doctoral) students?|phd eligibility stated", re.I)
MASTERS_ONLY = re.compile(r"(master'?s|graduate) students? only", re.I)
GRADUATE_REQ = re.compile(r"(must|should) (have|hold) (a |an )?(completed )?(bachelor'?s?|undergraduate|degree|master'?s?)"
                          r"|(bachelor'?s?|undergraduate) degree (is )?required|recent graduates?|graduates? only"
                          r"|completed (a |an )?(bachelor|degree)|degree completion", re.I)
EXPERIENCE = re.compile(r"(\d+)\+?\s*(?:-\s*\d+\s*)?years?(?:'| of)? (?:professional |industry |relevant |work )?experience", re.I)
GROUP_RESTRICT = re.compile(r"\b(women|female|underrepresented|minorit|veteran|indigenous|black|latin[ao]|lgbt)", re.I)
AGE_RESTRICT = re.compile(r"\b(age[sd]?|under|below|aged)\s*(\d{2})\b|\b(\d{2})\s*(years? old|or younger|and under)", re.I)
ENTITY_REQ = re.compile(r"(registered|incorporated) (company|startup|entity)|dpiit|startup entity|existing (company|startup)", re.I)
ENROLLED_THROUGH = re.compile(r"enrolled .{0,60}(entire|whole|full) (internship|duration)", re.I)
TEAM_ONLY = re.compile(r"existing registered teams only|registered[- ]team[- ]only|invite[- ]only|invitation only", re.I)


def assess(opp: dict, profile: dict, now: datetime | None = None) -> tuple[str, list[str]]:
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    text = " ".join(str(opp.get(k) or "") for k in (
        "eligibility_text", "sheet_eligibility_reason", "applications_open_raw", "notes", "name"))

    # temporal status first: an opportunity you cannot apply to is not "eligible"
    dl = opp.get("deadline_utc")
    recurring = (opp.get("access_class") == "historically_open") or bool(opp.get("recurrence")) or bool(opp.get("next_cycle"))
    if dl:
        try:
            dlt = datetime.fromisoformat(dl)
        except ValueError:
            dlt = None
        if dlt and dlt < now and not opp.get("rolling"):
            if recurring:
                return "closed_watch", [f"Deadline {dl[:10]} passed; recurring or next cycle noted"]
            return "deadline_passed", [f"Deadline {dl[:10]} passed ({opp.get('deadline_quality')})"]
    if (opp.get("status_raw") or "").upper().startswith("CLOSED") and not opp.get("rolling"):
        return "closed_watch", [f"Workbook status {opp.get('status_raw')}"]

    hard: list[str] = []
    soft: list[str] = []
    later: list[str] = []

    if "[VERIFIED BLOCK]" in text:
        snippet = text.split("[VERIFIED BLOCK]", 1)[1].strip()[:180]
        hard.append(f"Verified restriction (blocks unless you hold the named authorization or affiliation): {snippet}")
    if ENROLLED_THROUGH.search(text) and str(profile.get("graduation") or "") <= "2027-06":
        soft.append("Requires staying enrolled for the whole internship; you graduate around June 2027")
    if opp.get("undergrad_eligible") == "no":
        hard.append("Workbook says undergraduates are not eligible")
    if PHD_ONLY.search(text):
        hard.append("Text indicates PhD students only")
    if MASTERS_ONLY.search(text):
        hard.append("Text indicates master's/graduate students only")
    m = NATIONALITY_BLOCK.search(text)
    if m and not re.search(r"india|indian", m.group(0), re.I):
        if profile.get("citizenship") in (None, "", "unknown"):
            soft.append(f"Nationality/residency limit ('{m.group(0)}'); citizenship unknown in profile")
        else:
            hard.append(f"Nationality/residency limit: '{m.group(0)}'")
    if opp.get("intl_allowed") == "no" and not is_india(opp.get("country"), opp.get("region")):
        hard.append("International applicants not allowed and the opportunity is outside India")
    if TEAM_ONLY.search(text):
        hard.append("Restricted to existing/invited participants")
    if ENTITY_REQ.search(text):
        soft.append("Requires a registered startup entity")
    if GRADUATE_REQ.search(text):
        later.append(f"Requires a completed degree (graduation expected {profile.get('graduation', 'unknown')})")
    for em in EXPERIENCE.finditer(text):
        yrs = int(em.group(1))
        if yrs >= 2:
            later.append(f"Asks for {yrs}+ years of experience")
            break
    if GROUP_RESTRICT.search(text):
        soft.append("Restricted to a specific group; eligibility depends on facts not in the profile")
    if AGE_RESTRICT.search(text):
        soft.append("Age limit stated; age not in profile")
    sheet = (opp.get("sheet_eligibility") or "").lower()
    if sheet.startswith("not currently eligible") or sheet.startswith("not eligible"):
        later.append(f"Workbook assessment: {opp.get('sheet_eligibility')}")
    elif sheet.startswith("eligible later"):
        later.append("Workbook assessment: eligible later")
    elif sheet.startswith(("eligibility unclear", "needs individual", "requires individual")):
        soft.append(f"Workbook assessment: {opp.get('sheet_eligibility')}")

    abroad_in_person = (opp.get("location_mode") == "in_person" and not is_india(opp.get("country"), opp.get("region"))
                        and not is_global(opp.get("country")))

    if hard:
        return "ineligible", hard + later + soft
    if later:
        return "eligible_later", later + soft
    if abroad_in_person and profile.get("relocation") not in ("yes", "true", True):
        reasons.append(f"In person in {opp.get('country')}; relocation/travel preference unknown")
        return "travel_or_relocation", reasons + soft
    if soft:
        return "needs_check", soft
    ok = []
    if opp.get("undergrad_eligible") in ("yes", "conditional"):
        ok.append("Undergraduates eligible per workbook")
    if opp.get("intl_allowed") in ("yes", "conditional") or is_india(opp.get("country"), opp.get("region")):
        ok.append("Open to India-based applicants per workbook")
    if not ok:
        return "needs_check", ["No blocker found, but undergraduate and international eligibility are not stated"]
    return "eligible_likely", ok


STATUS_ORDER = ["eligible_likely", "needs_check", "travel_or_relocation", "eligible_later", "closed_watch",
                "deadline_passed", "ineligible"]
