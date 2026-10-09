"""Execution cockpit: action items, plan generation, outcome logging and calibration.

Calibration uses conjugate Beta updates with a power-prior discount: each real
outcome counts as `weight` (< 1) of an observation, because one person's outcomes
in one season are weak evidence about the underlying rate. The previous
distribution is kept in parameter_history, so every update can be inspected or undone.
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone

from . import service as S
from .db import now_iso, one, rows, tx
from .sim.params import Dist

HORIZONS = [("24h", 1), ("72h", 3), ("7d", 7), ("14d", 14), ("30d", 30), ("90d", 90), ("6m", 182), ("12m", 365)]

# which parameter an outcome of an action kind informs
OUTCOME_PARAMS = {
    "outreach_faculty": "p_reply_faculty", "outreach_founders": "p_reply_founder",
    "research_intern_applications": "p_research_intern_offer", "startup_applications": "p_startup_offer_targeted",
    "bigtech_applications": "p_job_offer_cold_apply", "predoc_applications": "p_predoc_offer",
    "hackathons_q4": "p_hackathon_place", "oss_eval_contribs": "p_oss_merge",
}


def upsert_action(con, body: dict) -> dict:
    aid = body.get("id") or "ACT-" + uuid.uuid4().hex[:8]
    existing = one(con, "SELECT * FROM action_item WHERE id=?", (aid,))
    fields = ["title", "kind", "reason", "objective", "evidence", "prerequisites", "effort_hours", "attention",
              "automation", "dependencies", "outcomes", "risk", "success_criteria", "failure_criteria", "due",
              "review_on", "alternatives", "unlocks", "horizon", "status", "opportunity_id", "strategy_action",
              "sim_run_id", "origin"]
    with tx(con):
        if existing:
            for f in fields:
                if f in body:
                    con.execute(f"UPDATE action_item SET {f}=?, updated_at=? WHERE id=?", (body[f], now_iso(), aid))
        else:
            con.execute("INSERT INTO action_item(id, created_at, updated_at) VALUES(?,?,?)", (aid, now_iso(), now_iso()))
            for f in fields:
                if f in body:
                    con.execute(f"UPDATE action_item SET {f}=? WHERE id=?", (body[f], aid))
    return one(con, "SELECT * FROM action_item WHERE id=?", (aid,))


def _horizon_for(days: float) -> str:
    for name, d in HORIZONS:
        if days <= d:
            return name
    return "later"


def generate_plan(con, run_id: str | None, strategy_id: str | None) -> dict:
    """Turn a simulated strategy into dated action items.

    Each item carries the simulated completion and outcome statistics, the deadline and
    its evidence basis, the prerequisites, what it unlocks, and how much of it AI can do.
    Existing generated items for the same run/strategy are replaced; user items are kept.
    """
    run = S.get_run(con, run_id) if run_id else None
    if run is None:
        latest = one(con, "SELECT id FROM sim_run ORDER BY created_at DESC LIMIT 1")
        if not latest:
            raise ValueError("run a simulation first")
        run = S.get_run(con, latest["id"])
    sid = strategy_id or run["analysis"]["ranking"][0]["strategy"]
    res = run["strategy_results"][sid]
    model = S.build_model(con)
    spec = next(s for s in run["strategies"] if s["id"] == sid)
    start = datetime.fromisoformat(run["start_date"]).replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    now = datetime.now(timezone.utc)
    produces = {}
    for a in model.actions:
        toks = set((a.effects.get("tokens") or {}).keys())
        for st in a.stages:
            for o in st.outcomes:
                toks |= set(o.tokens)
        produces[a.id] = toks
    consumers = {}
    for a in model.actions:
        def walk(c, out):
            if not c:
                return
            if "token" in c:
                out.add(c["token"])
            for k in ("all", "any"):
                for x in c.get(k, []):
                    walk(x, out)
        need = set()
        walk(a.requires_spec, need)
        for st in a.stages:
            for o in st.outcomes:
                for sh in (o.p.shifts if o.p else []):
                    if "token" in sh:
                        need.add(sh["token"])
        consumers[a.id] = need
    items = []
    with tx(con):
        con.execute("DELETE FROM action_item WHERE origin='plan' AND status='todo'")
    for aid in spec["actions"] + spec.get("contingent", []):
        stt = res["action_stats"].get(aid)
        if not stt:
            continue
        a = model.action(aid)
        comp_week = stt["mean_completion_week"]
        due_dt = (start + timedelta(weeks=a.deadline_week)) if a.deadline_week is not None else (
            start + timedelta(weeks=comp_week) if comp_week is not None else None)
        days_out = (due_dt - now).total_seconds() / 86400 if due_dt else 365
        unlocks = sorted({b for b, need in consumers.items() if produces[aid] & need and b != aid})
        lo, mo, hi = a.effort
        outs = stt["outcomes"]
        top_out = sorted(outs.items(), key=lambda kv: -kv[1])[:3]
        contingent = aid in spec.get("contingent", [])
        body = {
            "title": a.name, "kind": a.kind, "origin": "plan", "status": "todo", "sim_run_id": run["id"],
            "strategy_action": aid, "opportunity_id": a.opportunity_id,
            "reason": f"Part of '{spec.get('name', sid)}'. Completed in {stt['p_done']:.0%} of simulated worlds"
                      + (f"; missed in {stt['p_missed']:.0%}" if stt["p_missed"] > 0.01 else "")
                      + (" (contingent: only if its rule fires)" if contingent else "") + ".",
            "objective": run["objective"].get("name"),
            "evidence": f"Deadline basis: {a.deadline_basis or 'no deadline'}."
                        + (f" External dependency: {a.external_dependency}" if a.external_dependency else ""),
            "prerequisites": describe_req(a.requires_spec),
            "effort_hours": float(mo),
            "attention": f"{lo:g}–{hi:g} h estimated before planning-fallacy correction; "
                         f"{(1 - a.automatable):.0%} needs your own attention",
            "automation": f"{a.automatable:.0%} of the work can be AI-assisted (drafting, code, data runs); "
                          "review time is not automatable",
            "dependencies": ", ".join(sorted(consumers[aid])) or None,
            "outcomes": "; ".join(f"{k}: {v:.0%}" for k, v in top_out) if top_out else "Completion itself",
            "risk": (f"Missed in {stt['p_missed']:.0%} of worlds" if stt["p_missed"] > 0.05 else "Low schedule risk")
                    + ("; depends on another person" if a.external_dependency else ""),
            "success_criteria": "Submitted/completed before the deadline" if a.deadline_week is not None
                                else "Completed and recorded in the cockpit",
            "failure_criteria": "Deadline passes without submission" if a.deadline_week is not None
                                else "No progress by the review date",
            "due": due_dt.date().isoformat() if due_dt else None,
            "review_on": (min(due_dt, now + timedelta(days=7)) if due_dt else now + timedelta(days=7)).date().isoformat(),
            "alternatives": None, "unlocks": ", ".join(unlocks) or None,
            "horizon": _horizon_for(days_out),
        }
        items.append(upsert_action(con, body))
    items.sort(key=lambda r: r["due"] or "9999")
    return {"strategy": sid, "run_id": run["id"], "items": items}


def describe_req(spec) -> str | None:
    from .sim.conditions import describe
    return None if spec is None else describe(spec)


def record_outcome(con, body: dict) -> dict:
    """Log a real-world outcome; optionally update the parameter it informs.

    body: {action_id?, strategy_action?, event_type, result, successes?, trials?, param_name?, weight?, notes?}
    """
    oid = "OUT-" + uuid.uuid4().hex[:8]
    param = body.get("param_name") or OUTCOME_PARAMS.get(body.get("strategy_action") or "")
    succ, trials = body.get("successes"), body.get("trials")
    update = None
    with tx(con):
        con.execute("INSERT INTO outcome VALUES(?,?,?,?,?,?,?,?,?)",
                    (oid, now_iso(), body.get("action_id"), body.get("event_type", "result"), body.get("result"),
                     param, succ, trials, body.get("notes")))
        if body.get("action_id") and body.get("mark_done"):
            con.execute("UPDATE action_item SET status='done', updated_at=? WHERE id=?", (now_iso(), body["action_id"]))
    if param and succ is not None and trials:
        update = calibrate(con, param, int(succ), int(trials), float(body.get("weight", 0.5)))
    return {"id": oid, "param_update": update}


def calibrate(con, param: str, successes: int, trials: int, weight: float = 0.5) -> dict:
    p = one(con, "SELECT * FROM parameter WHERE name=?", (param,))
    if not p:
        raise KeyError(param)
    d = Dist.parse(p["dist"])
    if d.kind != "beta":
        raise ValueError(f"{param} is {d.kind}; only beta parameters are calibrated from counts")
    if successes > trials or trials <= 0:
        raise ValueError("need 0 <= successes <= trials and trials > 0")
    a, b = d.args
    a2, b2 = a + weight * successes, b + weight * (trials - successes)
    new = f"beta({a2:.3g}, {b2:.3g})"
    origin = "calibrated" if p["origin"] != "calibrated" else "calibrated"
    S.update_parameter(con, param, new, origin,
                       (p["notes"] or "") + f" | updated {datetime.now().date()}: {successes}/{trials} observed at weight {weight}",
                       reason=f"outcome log {successes}/{trials}, power-prior weight {weight}")
    return {"param": param, "before": p["dist"], "after": new, "prior_mean": a / (a + b), "posterior_mean": a2 / (a2 + b2),
            "note": "Power-prior update: observations are down-weighted because they come from a small, "
                    "non-random sample of one person's attempts."}


def upsert_forecast(con, body: dict) -> dict:
    fid = body.get("id") or "FC-" + uuid.uuid4().hex[:8]
    ex = one(con, "SELECT * FROM forecast WHERE id=?", (fid,))
    with tx(con):
        if not ex:
            con.execute("INSERT INTO forecast VALUES(?,?,?,?,?,?,?,?,?)",
                        (fid, now_iso(), body["question"], float(body["prob"]), body.get("resolve_by"), None, None,
                         body.get("sim_run_id"), body.get("notes")))
        elif "outcome" in body:
            con.execute("UPDATE forecast SET outcome=?, resolved_at=? WHERE id=?",
                        (int(bool(body["outcome"])), now_iso(), fid))
    return one(con, "SELECT * FROM forecast WHERE id=?", (fid,))


def forecast_scores(con) -> dict:
    res = rows(con, "SELECT prob, outcome FROM forecast WHERE outcome IS NOT NULL")
    if not res:
        return {"n": 0}
    brier = sum((r["prob"] - r["outcome"]) ** 2 for r in res) / len(res)
    logs = [-(math.log(max(r["prob"], 1e-6)) if r["outcome"] else math.log(max(1 - r["prob"], 1e-6))) for r in res]
    bins = {}
    for r in res:
        k = min(int(r["prob"] * 5), 4)
        bins.setdefault(k, []).append(r)
    calib = [{"bin": f"{k * 20}-{k * 20 + 20}%", "n": len(v), "mean_prob": sum(x["prob"] for x in v) / len(v),
              "observed": sum(x["outcome"] for x in v) / len(v)} for k, v in sorted(bins.items())]
    return {"n": len(res), "brier": brier, "log_loss": sum(logs) / len(logs), "calibration": calib,
            "note": "With few resolved forecasts these scores are noisy; one surprise is not evidence of a bad model."}
