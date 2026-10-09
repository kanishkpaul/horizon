"""Non-destructive import of the original workbooks into the knowledge store.

Originals are read from data/raw (read-only copies with SHA256SUMS). Every
original field is preserved in raw_json; normalized columns sit beside them.
Imported facts become claims attributed to the workbook, graded by the
workbook's own verification labels, never upgraded.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import openpyxl

from . import normalize as N
from .db import ROOT, now_iso, set_meta, tx

RAW = ROOT / "data" / "raw"
RADAR = RAW / "MASTER_AI_OPPORTUNITY_RADAR.xlsx"
MEETUPS = RAW / "Kolkata_Online_Meetups_Oct2026_Jan2027.xlsx"
RADAR_ORIGIN = "radar_2026-10-03"
MEETUP_ORIGIN = "meetups_2026-10-04"
RADAR_SOURCE_ID = "SRC-WB-RADAR"
MEETUP_SOURCE_ID = "SRC-WB-MEETUPS"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dataset_version() -> str:
    h = hashlib.sha256()
    for p in (RADAR, MEETUPS):
        h.update(sha256(p).encode())
    return "ds-" + h.hexdigest()[:12]


def _ser(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def table_rows(ws, tname: str) -> list[dict]:
    t = ws.tables[tname]
    m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", t.ref)
    data = list(ws.iter_rows(min_row=int(m.group(2)), max_row=int(m.group(4)), values_only=True))
    hdr = data[0]
    return [dict(zip(hdr, r)) for r in data[1:] if any(v is not None for v in r)]


def src_id_for_url(url: str) -> str:
    return "SRC-" + hashlib.sha1(url.encode()).hexdigest()[:12]


def org_id_for(name: str) -> str:
    return "ORG-" + hashlib.sha1(name.strip().lower().encode()).hexdigest()[:10]


def grade_from_sheet(verification: str | None, confidence: str | None) -> str:
    v, c = (verification or "").upper(), (confidence or "").lower()
    if v == "COULD_NOT_VERIFY" or c == "low":
        return "D"
    if v == "PARTIAL" or c == "medium":
        return "C"
    return "B"  # never A: Horizon has not itself read the primary page


def access_class(verification: str | None, status: str | None) -> str:
    v, s = (verification or "").upper(), (status or "").upper()
    if v == "COULD_NOT_VERIFY":
        return "unverified_lead"
    if v == "VERIFIED_HISTORICAL" or s.startswith("CLOSED") or s == "PAUSED":
        return "historically_open"
    if v == "PARTIAL":
        return "partially_verified"
    if v == "VERIFIED_CURRENT":
        return "verified_open"
    return "unverified_lead"


def import_all(con: sqlite3.Connection) -> dict:
    stats = {}
    origins = (RADAR_ORIGIN, MEETUP_ORIGIN)
    with tx(con):
        # Re-import replaces only rows this importer owns; user and agent rows survive.
        # Sources are keyed by URL hash and inserted with OR IGNORE, so they are never deleted.
        con.execute("DELETE FROM claim WHERE recorded_by LIKE 'import:%'")
        con.execute("DELETE FROM edge WHERE rel IN ('offered_by', 'cites', 'part_of', 'works_at') AND inferred = 0")
        for table in ("opportunity", "person", "event", "outreach_target", "search_gap"):
            con.execute(f"DELETE FROM {table} WHERE origin IN (?, ?)", origins)
        stats.update(_import_radar(con))
        stats.update(_import_meetups(con))
        set_meta(con, "dataset_version", dataset_version())
        set_meta(con, "imported_at", now_iso())
        set_meta(con, "raw_sha256", {p.name: sha256(p) for p in (RADAR, MEETUPS)})
    return stats


def _add_source(con, sid, kind, url=None, local_ref=None, title=None, publisher=None, quality=None,
                accessed=None, group=None, source_date=None):
    con.execute(
        "INSERT OR IGNORE INTO source(id, kind, url, local_ref, title, publisher, source_date, accessed_at, quality,"
        " independence_group, recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (sid, kind, url, local_ref, title, publisher, source_date, accessed, quality, group, now_iso()),
    )


def _claim(con, cid, stype, sid_, pred, value, value_norm, source_id, accessed, valid_from, method, grade,
           recorded_by, notes=None, valid_to=None):
    con.execute(
        "INSERT OR REPLACE INTO claim(id, subject_type, subject_id, predicate, value, value_norm, source_id,"
        " source_date, accessed_at, valid_from, valid_to, verification_method, evidence_grade, status,"
        " recorded_at, recorded_by, notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?)",
        (cid, stype, sid_, pred, None if value is None else str(value), value_norm, source_id, None, accessed,
         valid_from, valid_to, method, grade, now_iso(), recorded_by, notes),
    )


def _upsert_org(con, name, parent=None, url=None, countries=None, count=None, raw=None, origin=RADAR_ORIGIN):
    oid = org_id_for(name)
    con.execute(
        "INSERT INTO organization(id, name, parent, url, countries, opp_count, origin, raw_json, recorded_at)"
        " VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET"
        " parent=COALESCE(organization.parent, excluded.parent), url=COALESCE(organization.url, excluded.url),"
        " countries=COALESCE(organization.countries, excluded.countries),"
        " opp_count=COALESCE(excluded.opp_count, organization.opp_count)",
        (oid, name.strip(), parent, url, countries, count, origin, json.dumps(raw, default=str) if raw else None,
         now_iso()),
    )
    return oid


def _import_radar(con) -> dict:
    wb = openpyxl.load_workbook(RADAR, data_only=True)
    _add_source(con, RADAR_SOURCE_ID, "workbook", local_ref=str(RADAR.relative_to(ROOT)),
                title="MASTER_AI_OPPORTUNITY_RADAR.xlsx (built by Codex, research cutoff 2026-10-03)",
                publisher="Codex (AI research agent)", quality="AI-compiled secondary record",
                accessed="2026-10-09", group="radar_workbook", source_date="2026-10-03")

    # source registry
    for r in table_rows(wb["26_SOURCES"], "SourcesTable"):
        url = N.clean(r["Source URL"])
        if not url:
            continue
        _add_source(con, src_id_for_url(url), "url", url=url, publisher=N.clean(r["Organization"]),
                    quality=N.clean(r["Source quality"]), accessed=str(r["Last verified date"])[:10],
                    group=re.sub(r"^https?://(www\.)?", "", url).split("/")[0])

    # organizations inventory
    for r in table_rows(wb["28_ORGANIZATIONS"], "OrganizationsTable"):
        if N.clean(r["Organization"]):
            _upsert_org(con, r["Organization"], N.clean(r["Parent organization"]), N.clean(r["Official URL"]),
                        N.clean(r["Countries"]), int(r["Opportunities"] or 0), {k: _ser(v) for k, v in r.items()})

    # view membership
    views: dict[str, list[str]] = {}
    for ws in wb.worksheets:
        if ws.title in ("00_README", "01_ALL_OPPORTUNITIES", "26_SOURCES", "27_SEARCH_GAPS", "28_ORGANIZATIONS",
                        "30_COLD_OUTREACH"):
            continue
        for tn in ws.tables:
            for r in table_rows(ws, tn):
                if r.get("Opportunity ID"):
                    views.setdefault(r["Opportunity ID"], []).append(ws.title)

    opps = table_rows(wb["01_ALL_OPPORTUNITIES"], "AllOpportunities")
    n_claims = 0
    for r in opps:
        oid = r["Opportunity ID"]
        raw = {k: _ser(v) for k, v in r.items()}
        org_name = N.clean(r["Organization"]) or "Unknown"
        org = _upsert_org(con, org_name, N.clean(r["Parent organization"]))
        canon, mech = N.canonical_type(r["Opportunity type"], r["Opportunity subtype"])
        dl_utc, dl_q = N.normalize_deadline(r["Deadline"], r["Deadline timezone"], r["Deadline UTC"])
        money = "; ".join(f"{k}: {r[k]}" for k in ("Salary", "Stipend", "Grant amount", "Prize amount",
                          "Investment amount", "Compute credits", "Cloud credits", "API credits",
                          "Travel funding") if N.clean(r[k]))
        elig_text = " | ".join(str(r[k]) for k in ("Degree requirements", "Experience requirements",
                               "Technical prerequisites", "Other eligibility", "Nationality restrictions",
                               "Residency restrictions", "Age requirements") if N.clean(r[k]))
        status = N.clean(r["Current status"])
        ver = N.clean(r["Verification result"])
        conf = N.clean(r["Confidence level"])
        last_ver = str(r["Last verified date"])[:10] if r["Last verified date"] else None
        rolling = {"yes": 1, "no": 0}.get(N.norm_yes_no(r["Rolling?"]))
        con.execute(
            """INSERT INTO opportunity(id, name, org_id, org_name, type_raw, type_canonical, mechanism, access_class,
            status_raw, applications_open_raw, description, detail, why_it_matters, official_url, application_url,
            deadline_utc, deadline_raw, deadline_tz_raw, deadline_quality, opens_at, starts_at, ends_at, rolling,
            recurrence, next_cycle, country, region, remote, location_mode, intl_allowed, undergrad_eligible,
            student_required, eligibility_text, money_text, value_tags, rel_researcher, rel_developer, rel_founder,
            sheet_eligibility, sheet_eligibility_reason, confidence, verification_result, verification_scope,
            last_verified, info_gaps, notes, action_required, next_action_date, origin, views, raw_json,
            recorded_at, updated_at) VALUES(""" + ",".join("?" * 53) + ")",
            (oid, N.clean(r["Canonical opportunity name"]), org, org_name, N.clean(r["Opportunity type"]), canon,
             mech, access_class(ver, status), status, N.clean(r["Applications open?"]),
             N.clean(r["One-line description"]), N.clean(r["Detailed description"]), N.clean(r["Why it matters"]),
             N.clean(r["Official URL"]), N.clean(r["Application URL"]), dl_utc, N.clean(_ser(r["Deadline"])),
             N.clean(r["Deadline timezone"]), dl_q, N.clean(_ser(r["Opening date"])),
             N.clean(_ser(r["Event/start date"])), N.clean(_ser(r["End date"])), rolling,
             N.clean(r["Recurrence cadence"]), N.clean(r["Expected next cycle"]), N.clean(r["Country"]),
             N.clean(r["Region"]), N.clean(r["Remote?"]),
             N.location_mode(r["Remote?"], r["Hybrid?"], r["In-person/remote/hybrid"]),
             N.norm_yes_no(r["International applicants allowed?"]), N.norm_yes_no(r["Undergraduate eligible?"]),
             N.norm_yes_no(r["Student status required?"]), elig_text or None, money or None,
             N.clean(r["Value tags"]), N.clean(r["Researcher relevance"]), N.clean(r["AI developer relevance"]),
             N.clean(r["Founder relevance"]), N.clean(r["Current eligibility assessment"]),
             N.clean(r["Reason for eligibility assessment"]), conf, ver, N.clean(r["Verification scope"]),
             last_ver, N.clean(r["Information gaps"]), N.clean(r["Notes"]), N.clean(r["Action required"]),
             N.clean(_ser(r["Next action date"])), RADAR_ORIGIN, json.dumps(views.get(oid, [])),
             json.dumps(raw, default=str), now_iso(), now_iso()),
        )
        # claims: what the workbook asserts, attributed to the URL it cites
        cited = N.clean(r["Source 1"]) or N.clean(r["Official URL"])
        sid = src_id_for_url(cited) if cited else RADAR_SOURCE_ID
        if cited:
            _add_source(con, sid, "url", url=cited, accessed=last_ver,
                        group=re.sub(r"^https?://(www\.)?", "", cited).split("/")[0])
        grade = grade_from_sheet(ver, conf)
        note = f"Asserted by radar workbook ({ver}, confidence {conf}); not re-verified by Horizon."
        facts = [
            ("exists", N.clean(r["Canonical opportunity name"]), None),
            ("status", status, status),
            ("applications_open", N.clean(r["Applications open?"]), N.norm_yes_no(r["Applications open?"])),
            ("deadline", N.clean(_ser(r["Deadline"])), dl_utc),
            ("opens_at", N.clean(_ser(r["Opening date"])), None),
            ("starts_at", N.clean(_ser(r["Event/start date"])), None),
            ("undergrad_eligible", N.clean(r["Undergraduate eligible?"]), N.norm_yes_no(r["Undergraduate eligible?"])),
            ("international_allowed", N.clean(r["International applicants allowed?"]),
             N.norm_yes_no(r["International applicants allowed?"])),
            ("location_mode", N.clean(r["In-person/remote/hybrid"]) or N.clean(r["Remote?"]),
             N.location_mode(r["Remote?"], r["Hybrid?"], r["In-person/remote/hybrid"])),
            ("money", money or None, None),
            ("eligibility_text", elig_text or None, None),
            ("next_cycle_expected", N.clean(r["Expected next cycle"]), None),
        ]
        for pred, val, vn in facts:
            if val is None:
                continue
            n_claims += 1
            _claim(con, f"CLM-{oid}-{pred}", "opportunity", oid, pred, val, vn, sid, last_ver, last_ver,
                   "imported_from_ai_workbook", grade, "import:" + RADAR_ORIGIN, note)
        con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, confidence, recorded_at)"
                    " VALUES('opportunity', ?, 'offered_by', 'organization', ?, 0, 'B', ?)", (oid, org, now_iso()))
        for k in ("Source 1", "Source 2", "Source 3"):
            u = N.clean(r[k])
            if u:
                _add_source(con, src_id_for_url(u), "url", url=u, accessed=last_ver,
                            group=re.sub(r"^https?://(www\.)?", "", u).split("/")[0])
                con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, recorded_at)"
                            " VALUES('opportunity', ?, 'cites', 'source', ?, 0, ?)", (oid, src_id_for_url(u), now_iso()))
        parent = N.clean(r["Parent organization"])
        if parent and parent != org_name:
            pid = _upsert_org(con, parent)
            con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, recorded_at)"
                        " VALUES('organization', ?, 'part_of', 'organization', ?, 0, ?)", (org, pid, now_iso()))

    for i, r in enumerate(table_rows(wb["27_SEARCH_GAPS"], "SearchGapsTable"), 1):
        con.execute("INSERT INTO search_gap VALUES(?,?,?,?)",
                    (f"GAP-{i:04d}", N.clean(r["Workstream"]), N.clean(r["Coverage gap / limitation"]), RADAR_ORIGIN))

    n_out = 0
    for r in table_rows(wb["30_COLD_OUTREACH"], "ColdOutreachTable"):
        n_out += 1
        tid = f"OUT-{n_out:03d}"
        entity = N.clean(r["Entity"]) or "Unknown"
        org = _upsert_org(con, entity)
        contact = N.clean(r["Contact"])
        pid = None
        if contact and not re.search(r"\b(team|inbox|recruit|careers|hiring|admissions|office|desk)\b", contact.lower()):
            pid = "PER-" + hashlib.sha1(f"{contact}|{entity}".lower().encode()).hexdigest()[:10]
            con.execute("INSERT OR IGNORE INTO person(id, name, role, org_id, public_email, contact_type,"
                        " relationship, source_ref, origin, recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (pid, contact, N.clean(r["Contact type"]), org, N.clean(r["Public email"]),
                         N.clean(r["Contact type"]), "none (public contact)", N.clean(r["Source 1"]),
                         RADAR_ORIGIN, now_iso()))
            con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, recorded_at)"
                        " VALUES('person', ?, 'works_at', 'organization', ?, 0, ?)", (pid, org, now_iso()))
        con.execute(
            "INSERT INTO outreach_target VALUES(" + ",".join("?" * 22) + ")",
            (tid, int(r["Priority"] or 999), N.clean(r["Wave"]), entity, contact, N.clean(r["Public email"]),
             N.clean(r["Contact type"]), N.clean(r["Suggested role / ask"]), N.clean(r["Why you fit"]),
             N.clean(r["Contribution to pitch"]), N.clean(r["Opening evidence"]), N.clean(r["Constraints / caveats"]),
             N.clean(r["Source 1"]), N.clean(r["Source 2"]), str(r["Research date"])[:10],
             N.clean(r["Outreach status"]), N.clean(_ser(r["Last contacted"])), N.clean(r["Follow-up notes"]),
             org, pid, RADAR_ORIGIN, json.dumps({k: _ser(v) for k, v in r.items()}, default=str)),
        )
    return {"opportunities": len(opps), "claims": n_claims, "outreach_targets": n_out,
            "views": sum(len(v) for v in views.values())}


MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}


def parse_meetup_date(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r"(\d{1,2})\s*([A-Za-z]{3})", text)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    mo = MONTHS[m.group(2).lower()]
    yr = 2027 if mo <= 6 else 2026
    try:
        return date(yr, mo, int(m.group(1))).isoformat()
    except ValueError:
        return None


def _import_meetups(con) -> dict:
    wb = openpyxl.load_workbook(MEETUPS, data_only=True)
    _add_source(con, MEETUP_SOURCE_ID, "workbook", local_ref=str(MEETUPS.relative_to(ROOT)),
                title="Kolkata_Online_Meetups_Oct2026_Jan2027.xlsx (built by Codex, snapshot 2026-10-04)",
                publisher="Codex (AI research agent)", quality="AI-compiled secondary record",
                accessed="2026-10-09", group="meetup_workbook", source_date="2026-10-04")
    n = 0
    for r in table_rows(wb["Events"], "MeetupEvents"):
        n += 1
        eid = f"EVT-{int(r['ID']):03d}" if str(r["ID"]).isdigit() else f"EVT-x{n:03d}"
        con.execute("INSERT INTO event VALUES(" + ",".join("?" * 16) + ")",
                    (eid, N.clean(r["Event"]), N.clean(r["Location"]), N.clean(r["Category"]),
                     N.clean(r["Date / recurrence"]), parse_meetup_date(N.clean(r["Date / recurrence"])),
                     N.clean(r["Time / timezone"]), N.clean(r["Venue / format"]), N.clean(r["Topic"]),
                     N.clean(r["Advertised fee"]), N.clean(r["Availability / uncertainty"]),
                     N.clean(r["Source URL"]), N.clean(r["Evidence"]), MEETUP_ORIGIN,
                     json.dumps({k: _ser(v) for k, v in r.items()}, default=str), now_iso()))
    k = 0
    for r in table_rows(wb["Unconfirmed leads"], "CommunityLeads"):
        k += 1
        con.execute("INSERT INTO event(id, name, location, category, when_text, topic, availability, source_url,"
                    " evidence, origin, raw_json, recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"EVL-{k:03d}", N.clean(r["Community / event"]), None, "unconfirmed_lead", None,
                     N.clean(r["Topic / format"]), N.clean(r["Reason not included"]), N.clean(r["Source URL"]),
                     "excluded by original research", MEETUP_ORIGIN,
                     json.dumps({kk: _ser(v) for kk, v in r.items()}, default=str), now_iso()))
    return {"events": n, "event_leads": k}
