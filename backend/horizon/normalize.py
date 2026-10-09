"""Field normalization for imported opportunity records.

Every function here is lossy by design, so callers keep the raw value next to the
normalized one. Rules are deliberately simple and listed in ASSUMPTIONS.md.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone

EXCEL_EPOCH = datetime(1899, 12, 30)

# canonical type -> (keywords matched against "type subtype" lowercase, mechanism)
TYPE_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("research_internship", ("research internship", "student researcher", "research intern"), "selective_application"),
    ("internship", ("internship", "intern"), "selective_application"),
    ("research_job", ("research job", "research engineer", "research scientist", "research role"), "selective_application"),
    ("job", ("job", "role", "employment", "hiring"), "selective_application"),
    ("research_fellowship", ("research fellowship", "phd fellowship", "fellows program"), "selective_application"),
    ("fellowship", ("fellowship", "residency", "scholar", "scholarship"), "selective_application"),
    ("hackathon", ("hackathon", "buildathon", "hack"), "competition"),
    ("competition", ("competition", "challenge", "benchmark", "prize", "shared task", "kaggle", "olympiad"), "competition"),
    ("accelerator", ("accelerator",), "selective_application"),
    ("incubator", ("incubator", "incubation"), "selective_application"),
    ("investment", ("investment", "venture", "seed fund", "angel", "financing", "loan"), "selective_application"),
    ("grant", ("grant", "funding", "fund"), "selective_application"),
    ("compute_credits", ("credit", "compute", "cloud", "api access", "gpu", "infrastructure", "data / model", "dataset"), "rolling_resource"),
    ("publication_venue", ("publication", "conference", "workshop", "journal", "paper"), "publication"),
    ("event", ("event", "summit", "meetup", "summer school", "school", "bootcamp"), "event"),
    ("open_source_program", ("open-source", "open source", "mentorship", "gsoc", "lfx"), "selective_application"),
    ("community", ("community", "network", "ecosystem", "membership", "standards", "cofounder matching", "working group"), "community"),
    ("education", ("education", "course", "program", "training", "degree", "admission"), "selective_application"),
    ("visa_mobility", ("visa", "mobility", "travel"), "rolling_resource"),
    ("government_program", ("government", "procurement", "public sector", "ministry"), "selective_application"),
    ("award", ("award", "recognition"), "selective_application"),
    ("early_access", ("early access", "beta", "preview", "waitlist"), "rolling_resource"),
    ("market_access", ("distribution", "market", "marketplace", "customer", "investor access"), "rolling_resource"),
    ("grant", ("ip financial", "assistance"), "selective_application"),
]


def canonical_type(type_raw: str | None, subtype: str | None) -> tuple[str, str]:
    t = f"{type_raw or ''} {subtype or ''}".lower()
    head = (type_raw or "").lower()
    # match on the primary type first, then fall back to subtype text
    for text in (head, t):
        for canon, kws, mech in TYPE_RULES:
            if any(k in text for k in kws):
                return canon, mech
    return "other", "other"


TZ_OFFSETS = {
    "aoe": -12, "anywhere on earth": -12, "utc-12": -12,
    "ist": 5.5, "asia/kolkata": 5.5, "asia/calcutta": 5.5, "india": 5.5,
    "utc": 0, "gmt": 0, "bst": 1, "uk time": 1, "cet": 1, "cest": 2,
    "pdt": -7, "pt": -7, "pst": -8, "edt": -4, "et": -4, "est": -5,
    "jst": 9, "asia/tokyo": 9, "kst": 9, "asia/seoul": 9, "sgt": 8, "asia/singapore": 8,
    "asia/hong_kong": 8, "beijing": 8, "gmt+8": 8, "gst": 4, "asia/dubai": 4,
}


def excel_serial_to_utc(x) -> datetime | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not (30000 < v < 80000):
        return None
    return (EXCEL_EPOCH + timedelta(days=v)).replace(tzinfo=timezone.utc)


def parse_offset(tz_text: str | None) -> float | None:
    if not tz_text:
        return None
    t = tz_text.lower()
    m = re.search(r"utc\s*([+-−])\s*(\d{1,2})(?::?(\d{2}))?", t)
    if m:
        sign = -1 if m.group(1) in "-−" else 1
        return sign * (int(m.group(2)) + (int(m.group(3) or 0) / 60))
    m = re.search(r"gmt\s*([+-])\s*(\d{1,2})", t)
    if m:
        return (-1 if m.group(1) == "-" else 1) * int(m.group(2))
    for key in sorted(TZ_OFFSETS, key=len, reverse=True):
        if re.search(rf"(^|[^a-z]){re.escape(key)}([^a-z]|$)", t):
            return TZ_OFFSETS[key]
    return None


def parse_clock(tz_text: str | None) -> time | None:
    if not tz_text:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", tz_text.lower())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3) == "pm" and h < 12:
        h += 12
    if m.group(3) == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return time(h, mi)


def parse_date(x) -> date | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    s = str(x).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def normalize_deadline(deadline_raw, tz_raw, utc_serial) -> tuple[str | None, str]:
    """Return (ISO UTC instant, quality label).

    exact_utc: workbook carried an exact UTC instant.
    date_tz_parsed: calendar date plus a parsed timezone/clock (23:59 if no clock).
    date_only_conservative: date known, timezone not; we use 00:00 IST on that date,
        i.e. treat the deadline as the end of the previous day in India.
    text_only: no machine-readable date.
    """
    exact = excel_serial_to_utc(utc_serial)
    if exact:
        return exact.isoformat(), "exact_utc"
    d = parse_date(deadline_raw)
    if not d:
        return None, "text_only" if deadline_raw else "none"
    off = parse_offset(tz_raw if isinstance(tz_raw, str) else None)
    if off is not None:
        clk = parse_clock(tz_raw) or time(23, 59)
        local = datetime.combine(d, clk)
        return (local - timedelta(hours=off)).replace(tzinfo=timezone.utc).isoformat(), "date_tz_parsed"
    local = datetime.combine(d, time(0, 0))
    return (local - timedelta(hours=5.5)).replace(tzinfo=timezone.utc).isoformat(), "date_only_conservative"


def norm_yes_no(x) -> str:
    """Collapse free-text yes/no fields to yes | no | conditional | unknown."""
    if x is None:
        return "unknown"
    s = str(x).strip().lower()
    if not s or s in ("none", "unknown", "unverified", "not stated", "could not verify", "not verified"):
        return "unknown"
    if s.startswith(("yes", "generally yes", "possible")):
        return "conditional" if any(k in s for k in ("subject", "rules", "dependent", "conditional", "specific")) else "yes"
    if s.startswith("no"):
        return "no"
    if any(k in s for k in ("conditional", "dependent", "varies", "invite", "existing", "only", "restricted")):
        return "conditional"
    return "unknown"


def location_mode(remote, hybrid, inperson_text) -> str:
    r, h = norm_yes_no(remote), norm_yes_no(hybrid)
    t = (str(inperson_text or "")).lower()
    if r == "yes" or "remote" in t or "online" in t or "virtual" in t:
        return "hybrid" if ("in-person" in t or "in person" in t) else "remote"
    if h == "yes" or "hybrid" in t:
        return "hybrid"
    if r == "no" or "in-person" in t or "in person" in t or "onsite" in t:
        return "in_person"
    return "unknown"


def clean(x) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return None if s in ("", "None") else s


def is_india(country: str | None, region: str | None = None) -> bool:
    s = f"{country or ''} {region or ''}".lower()
    return "india" in s or any(k in s for k in ("karnataka", "kerala", "tamil nadu", "kolkata", "bengal"))


def is_global(country: str | None) -> bool:
    s = (country or "").lower()
    return s.startswith("global") or "remote" in s or "online" in s or s == "multiple"
