"""Ingest structured output from research workers (verification, discovery, parameters).

Agent claims never overwrite history. A grade A/B claim that contradicts a workbook claim
marks the older claim `superseded` and updates the opportunity's current fields; a grade
C/D contradiction marks both sides `contradicted` and changes nothing else.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import normalize as N
from .db import ROOT, now_iso, one, tx
from .ingest import _add_source, _upsert_org, src_id_for_url

AGENTS = ROOT / "research" / "agents"

PRED_MAP = {  # agent predicate -> workbook claim predicate
    "deadline": "deadline", "status": "status", "applications_open": "applications_open",
    "undergrad_eligible": "undergrad_eligible", "nationality_restriction": "eligibility_text",
    "eligibility_note": "eligibility_text", "location_mode": "location_mode", "stipend_or_prize": "money",
    "next_cycle_expected": "next_cycle_expected", "exists": "exists",
}


def _domain(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]


def _iso_utc(v: str | None) -> str | None:
    if not v or v in ("true", "false"):
        return None
    try:
        if "T" in v:
            d = datetime.fromisoformat(v)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc).isoformat()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            iso, _ = N.normalize_deadline(v, None, None)  # date-only → conservative
            return iso
    except ValueError:
        return None
    return None


def ingest_verify(con: sqlite3.Connection, path: Path | None = None) -> dict:
    path = path or AGENTS / "verify" / "claims.jsonl"
    if not path.exists():
        return {"skipped": str(path)}
    claims = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    stats = {"claims": 0, "superseded": 0, "contradicted": 0, "new_opportunities": 0, "fields_updated": 0}
    with tx(con):
        con.execute("DELETE FROM claim WHERE recorded_by='agent:verify'")
        con.execute("UPDATE claim SET status='active', superseded_by=NULL WHERE superseded_by LIKE 'AGT-VER-%'")
        con.execute("DELETE FROM opportunity WHERE origin='verify_agent'")
        new_opps: dict[str, dict] = {}
        for c in claims:
            oid = c["opportunity_id"]
            if oid.startswith("NEW-"):
                new_opps.setdefault(oid, {"name": c["opportunity_name"], "claims": []})["claims"].append(c)
        for oid, d in new_opps.items():
            name = d["name"]
            canon, mech = N.canonical_type(name, None)
            dl = next((_iso_utc(x["value_normalized"]) for x in d["claims"]
                       if x["predicate"] == "deadline" and x["evidence_grade"] in "AB"), None)
            status = next((x["value"][:200] for x in d["claims"] if x["predicate"] == "status"), None)
            closed = any(x["predicate"] in ("status", "applications_open") and x["value_normalized"] == "false"
                         for x in d["claims"])
            urls = [x["source_url"] for x in d["claims"]]
            org = _upsert_org(con, name.split("(")[0].split(" - ")[0].strip()[:80], origin="verify_agent")
            con.execute(
                "INSERT INTO opportunity(id, name, org_id, org_name, type_canonical, mechanism, access_class, status_raw,"
                " description, official_url, deadline_utc, deadline_quality, origin, views, raw_json, recorded_at,"
                " updated_at, verification_result, confidence, last_verified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (oid, name, org, name.split("(")[0].strip(), canon, mech,
                 "historically_open" if closed else ("verified_open" if dl else "partially_verified"), status,
                 " ".join(x["value"] for x in d["claims"])[:1200], urls[0] if urls else None, dl,
                 "agent_verified" if dl else "none", "verify_agent", "[]", json.dumps(d["claims"]), now_iso(),
                 now_iso(), "HORIZON_AGENT_VERIFIED", "Medium", "2026-10-09"))
            stats["new_opportunities"] += 1
        for c in claims:
            url = c.get("source_url") or ""
            sid = src_id_for_url(url) if url else None
            if sid:
                _add_source(con, sid, "url", url=url, title=c.get("source_title"), accessed=c.get("accessed_at"),
                            group=_domain(url), source_date=c.get("source_date"))
            cid = "AGT-" + c["claim_id"]
            pred = PRED_MAP.get(c["predicate"], c["predicate"])
            con.execute(
                "INSERT OR REPLACE INTO claim(id, subject_type, subject_id, predicate, value, value_norm, source_id,"
                " source_date, accessed_at, valid_from, verification_method, evidence_grade, status, recorded_at,"
                " recorded_by, notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?)",
                ("AGT-" + c["claim_id"], "opportunity", c["opportunity_id"], pred, c["value"], c.get("value_normalized"),
                 sid, c.get("source_date"), c.get("accessed_at"), c.get("accessed_at"), c.get("verification_method"),
                 c.get("evidence_grade"), now_iso(), "agent:verify",
                 (c.get("notes") or "") + (f" | sheet value: {c['sheet_value']}" if c.get("sheet_value") else "")))
            stats["claims"] += 1
            oid = c["opportunity_id"]
            if oid.startswith("NEW-") or not one(con, "SELECT 1 x FROM opportunity WHERE id=?", (oid,)):
                continue
            strong = c.get("evidence_grade") in ("A", "B")
            if c.get("contradicts_sheet"):
                olds = [r[0] for r in con.execute(
                    "SELECT id FROM claim WHERE subject_id=? AND predicate=? AND recorded_by LIKE 'import:%'"
                    " AND status='active'", (oid, pred))]
                for old in olds:
                    if strong:
                        con.execute("UPDATE claim SET status='superseded', superseded_by=? WHERE id=?", (cid, old))
                        stats["superseded"] += 1
                    else:
                        con.execute("UPDATE claim SET status='contradicted', contradicts=? WHERE id=?", (cid, old))
                        con.execute("UPDATE claim SET status='contradicted', contradicts=? WHERE id=?", (old, cid))
                        stats["contradicted"] += 1
            if not strong:
                continue
            # update current fields from strong evidence
            if c["predicate"] == "deadline":
                iso = _iso_utc(c.get("value_normalized"))
                if iso:
                    con.execute("UPDATE opportunity SET deadline_utc=?, deadline_quality='agent_verified',"
                                " last_verified=?, updated_at=? WHERE id=?", (iso, c["accessed_at"], now_iso(), oid))
                    stats["fields_updated"] += 1
            elif c["predicate"] == "undergrad_eligible" and c.get("value_normalized") in ("false", "true"):
                con.execute("UPDATE opportunity SET undergrad_eligible=?, updated_at=? WHERE id=?",
                            ("no" if c["value_normalized"] == "false" else "yes", now_iso(), oid))
                stats["fields_updated"] += 1
            elif c["predicate"] in ("nationality_restriction", "eligibility_note"):
                block = c["predicate"] == "nationality_restriction" and c.get("value_normalized") == "true"
                tag = "[VERIFIED BLOCK]" if block else f"[verified {c['accessed_at']}]"
                con.execute("UPDATE opportunity SET eligibility_text = COALESCE(eligibility_text, '') || ? ,"
                            " updated_at=? WHERE id=?", (f" | {tag} {c['value']}", now_iso(), oid))
                stats["fields_updated"] += 1
            elif c["predicate"] in ("status", "applications_open"):
                if c.get("value_normalized") == "false":
                    con.execute("UPDATE opportunity SET access_class='historically_open', status_raw=?, updated_at=?"
                                " WHERE id=?", ("CLOSED (verified 2026-10-09)", now_iso(), oid))
                elif c.get("value_normalized") == "true":
                    con.execute("UPDATE opportunity SET access_class='verified_open', updated_at=? WHERE id=?",
                                (now_iso(), oid))
                stats["fields_updated"] += 1
            if strong:
                con.execute("UPDATE opportunity SET verification_result='HORIZON_AGENT_VERIFIED', last_verified=?"
                            " WHERE id=?", (c["accessed_at"], oid))
        con.execute("INSERT OR REPLACE INTO research_log VALUES(?,?,?,?,?,?,?)",
                    ("RL-verify-2026-10-09", now_iso(), "source_audit",
                     "Re-verify near-term opportunities and the ARR timeline against primary sources",
                     (AGENTS / "verify" / "summary.md").read_text() if (AGENTS / "verify" / "summary.md").exists() else "",
                     json.dumps([str(path.relative_to(ROOT))]), "done"))
    return stats


ACCESS_MAP = {
    "verified_open_opportunity": "verified_open", "historically_open_opportunity": "historically_open",
    "evidence_supported_potential_collaboration": "evidence_supported_collaboration",
    "speculative_created_opportunity_hypothesis": "speculative_hypothesis",
}


def ingest_discovery(con: sqlite3.Connection) -> dict:
    op_path = AGENTS / "discovery" / "opportunities.jsonl"
    hy_path = AGENTS / "discovery" / "creation_hypotheses.jsonl"
    stats = {"opportunities": 0, "hypotheses": 0}
    with tx(con):
        con.execute("DELETE FROM opportunity WHERE origin='discovery_agent'")
        con.execute("DELETE FROM claim WHERE recorded_by='agent:discovery'")
        con.execute("DELETE FROM hypothesis WHERE origin='discovery_agent'")
        if op_path.exists():
            for l in op_path.read_text().splitlines():
                if not l.strip():
                    continue
                o = json.loads(l)
                canon, mech = N.canonical_type(o.get("kind", "").replace("_", " ") + " " + o["name"], None)
                if o["kind"] in ("research_group_invites_collaborators", "hiring_signal_no_posting",
                                 "emerging_demand_signal"):
                    mech = "outreach"
                org = _upsert_org(con, o["organization"][:80], origin="discovery_agent")
                dl = _iso_utc(o.get("deadline")) if o.get("deadline") else None
                urls = o.get("source_urls") or []
                con.execute(
                    "INSERT INTO opportunity(id, name, org_id, org_name, type_raw, type_canonical, mechanism, access_class,"
                    " description, why_it_matters, official_url, deadline_utc, deadline_quality, location_mode,"
                    " eligibility_text, money_text, origin, views, raw_json, recorded_at, updated_at,"
                    " verification_result, confidence, last_verified, notes)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (o["id"], o["name"], org, o["organization"], o["kind"], canon, mech,
                     ACCESS_MAP.get(o["access_class"], o["access_class"]), o.get("description"), o.get("why_fit"),
                     urls[0] if urls else None, dl, "agent_reported" if dl else "none",
                     (o.get("location_mode") or "unknown").lower().replace("-", "_").split()[0] if o.get("location_mode") else "unknown",
                     o.get("eligibility_notes"), o.get("value_notes"), "discovery_agent", "[]", json.dumps(o), now_iso(),
                     now_iso(), "HORIZON_AGENT_DISCOVERED", {"A": "High", "B": "Medium"}.get(o.get("evidence_grade"), "Low"),
                     o.get("accessed_at"), o.get("notes")))
                for u, sd in zip(urls, o.get("source_dates") or [None] * len(urls)):
                    sid = src_id_for_url(u)
                    _add_source(con, sid, "url", url=u, accessed=o.get("accessed_at"), group=_domain(u), source_date=sd)
                    con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, recorded_at)"
                                " VALUES('opportunity', ?, 'cites', 'source', ?, 0, ?)", (o["id"], sid, now_iso()))
                con.execute("INSERT INTO edge(src_type, src_id, rel, dst_type, dst_id, inferred, confidence, recorded_at)"
                            " VALUES('opportunity', ?, 'offered_by', 'organization', ?, 0, ?, ?)",
                            (o["id"], org, o.get("evidence_grade"), now_iso()))
                con.execute("INSERT OR REPLACE INTO claim(id, subject_type, subject_id, predicate, value, source_id,"
                            " accessed_at, valid_from, verification_method, evidence_grade, status, recorded_at,"
                            " recorded_by, notes) VALUES(?,?,?,?,?,?,?,?,?,?,'active',?,?,?)",
                            (f"AGT-{o['id']}-exists", "opportunity", o["id"], "exists", o["description"],
                             src_id_for_url(urls[0]) if urls else None, o.get("accessed_at"), o.get("accessed_at"),
                             "primary_page_read" if o.get("evidence_grade") == "A" else "agent_research",
                             o.get("evidence_grade"), now_iso(), "agent:discovery", o.get("notes")))
                if dl:
                    con.execute("INSERT OR REPLACE INTO claim(id, subject_type, subject_id, predicate, value, value_norm,"
                                " source_id, accessed_at, valid_from, verification_method, evidence_grade, status,"
                                " recorded_at, recorded_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,'active',?,?)",
                                (f"AGT-{o['id']}-deadline", "opportunity", o["id"], "deadline", o["deadline"], dl,
                                 src_id_for_url(urls[0]) if urls else None, o.get("accessed_at"), o.get("accessed_at"),
                                 "agent_research", o.get("evidence_grade"), now_iso(), "agent:discovery"))
                stats["opportunities"] += 1
        if hy_path.exists():
            for l in hy_path.read_text().splitlines():
                if not l.strip():
                    continue
                h = json.loads(l)
                lo, hi = (h.get("demo_effort_hours_range") or [None, None])[:2]
                con.execute("INSERT OR REPLACE INTO hypothesis VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (h["id"], h["target_org"], h.get("target_group_or_role"), h.get("public_lead"),
                             h.get("problem"), json.dumps(h.get("evidence_problem_exists") or []),
                             h.get("why_this_person"), h.get("demonstration_needed"), lo, hi,
                             h.get("collaboration_form"), h.get("access_mechanism"), h.get("access_evidence"),
                             json.dumps(h.get("invalidators") or []), h.get("highest_information_value_next_step"),
                             h.get("classification"), h.get("upside_notes"), h.get("risks"), "open",
                             "discovery_agent", now_iso()))
                _upsert_org(con, h["target_org"][:80], origin="discovery_agent")
                stats["hypotheses"] += 1
        con.execute("INSERT OR REPLACE INTO research_log VALUES(?,?,?,?,?,?,?)",
                    ("RL-discovery-2026-10-09", now_iso(), "independent_discovery",
                     "Blank-slate discovery of formal, unadvertised and created opportunities",
                     (AGENTS / "discovery" / "summary.md").read_text() if (AGENTS / "discovery" / "summary.md").exists() else "",
                     json.dumps([str(op_path.relative_to(ROOT)), str(hy_path.relative_to(ROOT))]), "done"))
    return stats


def ingest_param_evidence(con: sqlite3.Connection) -> dict:
    path = AGENTS / "params" / "parameters.jsonl"
    if not path.exists():
        return {"skipped": True}
    n = 0
    with tx(con):
        con.execute("DELETE FROM claim WHERE recorded_by='agent:params'")
        for l in path.read_text().splitlines():
            if not l.strip():
                continue
            p = json.loads(l)
            srcs = p.get("sources") or []
            sid = None
            if srcs and srcs[0].get("url"):
                sid = src_id_for_url(srcs[0]["url"])
                _add_source(con, sid, "url", url=srcs[0]["url"], title=srcs[0].get("citation"),
                            accessed=p.get("accessed_at"), group=_domain(srcs[0]["url"]))
            val = {k: p.get(k) for k in ("estimate", "low", "high", "unit", "population")}
            con.execute("INSERT OR REPLACE INTO claim(id, subject_type, subject_id, predicate, value, value_norm,"
                        " source_id, accessed_at, valid_from, verification_method, evidence_grade, status, recorded_at,"
                        " recorded_by, notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?)",
                        ("AGT-" + p["param_id"], "evidence_parameter", p["name"], "estimate", json.dumps(val),
                         None if p.get("estimate") is None else str(p["estimate"]), sid, p.get("accessed_at"),
                         p.get("accessed_at"), p.get("origin"), p.get("evidence_grade"), now_iso(), "agent:params",
                         (p.get("transferability_to_this_person") or "") + " | prior: " + str(p.get("suggested_prior"))))
            n += 1
        con.execute("INSERT OR REPLACE INTO research_log VALUES(?,?,?,?,?,?,?)",
                    ("RL-params-2026-10-09", now_iso(), "empirical_parameters",
                     "Published base rates and human-performance evidence for simulator parameters",
                     (AGENTS / "params" / "summary.md").read_text() if (AGENTS / "params" / "summary.md").exists() else "",
                     json.dumps([str(path.relative_to(ROOT))]), "done"))
    return {"parameter_evidence": n}


def ingest_all(con) -> dict:
    return {"verify": ingest_verify(con), "discovery": ingest_discovery(con), "params": ingest_param_evidence(con)}
