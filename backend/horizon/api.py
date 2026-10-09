"""HTTP API (FastAPI). Serves the built frontend from frontend/dist when present."""
from __future__ import annotations

import csv
import io
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from . import eligibility, search
from . import service as S
from .db import ROOT, connect, get_meta, now_iso, one, rows, tx

app = FastAPI(title="Project Horizon", version="0.3.0")
_con = None
_lock = threading.RLock()


def con():
    global _con
    if _con is None:
        _con = connect()
        S.bootstrap(_con)
    return _con


def _json(o):
    return JSONResponse(json.loads(json.dumps(o, default=S._np)))


# ------------------------------------------------------------------ overview
@app.get("/api/overview")
def overview():
    c = con()
    now = datetime.now(timezone.utc)
    soon = (now + timedelta(days=45)).isoformat()
    deadlines = rows(c, "SELECT o.id, o.name, o.org_name, o.type_canonical, o.deadline_utc, o.deadline_quality,"
                        " o.access_class, a.status AS eligibility, a.fit FROM opportunity o"
                        " JOIN opportunity_assessment a ON a.opp_id=o.id WHERE o.deadline_utc BETWEEN ? AND ?"
                        " AND a.status IN ('eligible_likely','needs_check','travel_or_relocation')"
                        " ORDER BY o.deadline_utc LIMIT 40", (now.isoformat(), soon))
    counts = {r["status"]: r["n"] for r in rows(c, "SELECT status, COUNT(*) n FROM opportunity_assessment GROUP BY 1")}
    unknown_profile = rows(c, "SELECT id, label, notes FROM profile_item WHERE evidence_status IN ('unknown','assumed')")
    latest = one(c, "SELECT id, created_at, label, objective_id FROM sim_run ORDER BY created_at DESC LIMIT 1")
    return _json({
        "now": now.isoformat(), "dataset_version": get_meta(c, "dataset_version"),
        "imported_at": get_meta(c, "imported_at"),
        "counts": {
            "opportunities": one(c, "SELECT COUNT(*) n FROM opportunity")["n"],
            "claims": one(c, "SELECT COUNT(*) n FROM claim")["n"],
            "sources": one(c, "SELECT COUNT(*) n FROM source")["n"],
            "organizations": one(c, "SELECT COUNT(*) n FROM organization")["n"],
            "events": one(c, "SELECT COUNT(*) n FROM event")["n"],
            "hypotheses": one(c, "SELECT COUNT(*) n FROM hypothesis")["n"],
            "outreach_targets": one(c, "SELECT COUNT(*) n FROM outreach_target")["n"],
            "runs": one(c, "SELECT COUNT(*) n FROM sim_run")["n"],
            "eligibility": counts,
        },
        "upcoming_deadlines": deadlines, "profile_unknowns": unknown_profile, "latest_run": latest,
        "access_classes": rows(c, "SELECT access_class, COUNT(*) n FROM opportunity GROUP BY 1 ORDER BY 2 DESC"),
    })


# ------------------------------------------------------------------ opportunities
@app.get("/api/opportunities")
def opportunities(q: str | None = None, type: str | None = None, eligibility_status: str | None = None,
                  access: str | None = None, origin: str | None = None, deadline_before: str | None = None,
                  sort: str = "deadline", limit: int = 600, mode: str = "hybrid"):
    c = con()
    base = ("SELECT o.id, o.name, o.org_name, o.type_canonical, o.type_raw, o.mechanism, o.access_class, o.status_raw,"
            " o.deadline_utc, o.deadline_quality, o.country, o.location_mode, o.rel_researcher, o.rel_developer,"
            " o.rel_founder, o.confidence, o.verification_result, o.last_verified, o.money_text, o.origin,"
            " o.description, a.status AS eligibility, a.reasons_json, a.fit,"
            " (SELECT 1 FROM shortlist s WHERE s.opp_id=o.id) AS shortlisted"
            " FROM opportunity o LEFT JOIN opportunity_assessment a ON a.opp_id=o.id WHERE 1=1")
    args: list = []
    for col, val in (("o.type_canonical", type), ("a.status", eligibility_status), ("o.access_class", access),
                     ("o.origin", origin)):
        if val:
            vals = val.split(",")
            base += f" AND {col} IN ({','.join('?' * len(vals))})"
            args += vals
    if deadline_before:
        base += " AND o.deadline_utc IS NOT NULL AND o.deadline_utc <= ?"
        args.append(deadline_before)
    items = rows(c, base, args)
    for it in items:
        it["reasons"] = json.loads(it.pop("reasons_json") or "[]")
    if q:
        hits = search.hybrid(c, q, k=200, types=["opportunity"], mode=mode)
        rank = {h["doc_id"]: (i, h) for i, h in enumerate(hits)}
        items = [dict(it, search=rank[it["id"]][1]["signals"], search_rank=rank[it["id"]][0])
                 for it in items if it["id"] in rank]
        items.sort(key=lambda it: it["search_rank"])
    elif sort == "fit":
        items.sort(key=lambda it: -(it["fit"] or 0))
    elif sort == "deadline":
        now = datetime.now(timezone.utc).isoformat()
        items.sort(key=lambda it: (it["deadline_utc"] is None, it["deadline_utc"] < now if it["deadline_utc"] else False,
                                   it["deadline_utc"] or ""))
    return _json({"total": len(items), "items": items[:limit]})


@app.get("/api/opportunities/{oid}")
def opportunity(oid: str):
    c = con()
    o = one(c, "SELECT * FROM opportunity WHERE id=?", (oid,))
    if not o:
        raise HTTPException(404)
    o["raw"] = json.loads(o.pop("raw_json") or "{}")
    o["views"] = json.loads(o["views"] or "[]")
    a = one(c, "SELECT * FROM opportunity_assessment WHERE opp_id=?", (oid,))
    if a:
        a["reasons"] = json.loads(a.pop("reasons_json") or "[]")
    claims = rows(c, "SELECT c.*, s.url AS source_url, s.title AS source_title, s.kind AS source_kind,"
                     " s.independence_group FROM claim c LEFT JOIN source s ON s.id=c.source_id"
                     " WHERE c.subject_type='opportunity' AND c.subject_id=? ORDER BY c.predicate, c.recorded_at", (oid,))
    sources = rows(c, "SELECT s.* FROM edge e JOIN source s ON s.id=e.dst_id WHERE e.src_type='opportunity'"
                      " AND e.src_id=? AND e.rel='cites'", (oid,))
    org = one(c, "SELECT * FROM organization WHERE id=?", (o["org_id"],)) if o["org_id"] else None
    siblings = rows(c, "SELECT id, name, type_canonical, deadline_utc FROM opportunity WHERE org_id=? AND id<>? LIMIT 30",
                    (o["org_id"], oid)) if o["org_id"] else []
    sim = []
    for h in search.similar(c, "opportunity", oid, k=8, types=["opportunity"]):
        r = one(c, "SELECT id, name, org_name, type_canonical, deadline_utc FROM opportunity WHERE id=?", (h["doc_id"],))
        if r:
            sim.append(r | {"similarity": h["similarity"]})
    short = one(c, "SELECT * FROM shortlist WHERE opp_id=?", (oid,))
    return _json({"opportunity": o, "assessment": a, "claims": claims, "sources": sources, "organization": org,
                  "same_organization": siblings, "similar": sim, "shortlisted": bool(short),
                  "similarity_note": "Similarity is semantic closeness of descriptions, not evidence of equivalence."})


@app.post("/api/shortlist/{oid}")
def shortlist_add(oid: str, body: dict = Body(default={})):
    S.set_shortlist(con(), oid, True, body.get("note"))
    return {"ok": True}


@app.delete("/api/shortlist/{oid}")
def shortlist_remove(oid: str):
    S.set_shortlist(con(), oid, False)
    return {"ok": True}


@app.get("/api/shortlist")
def shortlist():
    return _json(S.shortlist(con()))


# ------------------------------------------------------------------ search
@app.get("/api/search")
def search_all(q: str, mode: str = "hybrid", types: str | None = None, k: int = 25):
    c = con()
    hits = search.hybrid(c, q, k=k, types=types.split(",") if types else None, mode=mode)
    out = []
    for h in hits:
        t, i = h["doc_type"], h["doc_id"]
        r = c.execute("SELECT title, body FROM doc_fts WHERE doc_type=? AND doc_id=?", (t, i)).fetchone()
        out.append(h | {"title": r[0] if r else i, "snippet": (r[1] or "")[:220] if r else ""})
    return _json({"query": q, "mode": mode, "results": out})


# ------------------------------------------------------------------ graph
@app.get("/api/graph")
def graph(focus: str | None = None, limit: int = 220):
    """Relationship graph: organizations, opportunities, people, hypotheses, profile assets."""
    c = con()
    nodes, edges = {}, []

    def node(nid, label, kind, **kw):
        nodes.setdefault(nid, {"id": nid, "label": label, "kind": kind, **kw})

    node("me", "You", "self")
    for p in rows(c, "SELECT id, label, dimension, evidence_status FROM profile_item WHERE dimension IN"
                     " ('research','network','engineering')"):
        node(p["id"], p["label"], "asset" if p["dimension"] != "network" else "relationship",
             evidence=p["evidence_status"])
        edges.append({"source": "me", "target": p["id"], "rel": "has" if p["dimension"] != "network" else "knows"})
    if focus:
        opps = rows(c, "SELECT o.id, o.name, o.org_id, o.org_name, o.type_canonical, a.status, a.fit FROM opportunity o"
                       " JOIN opportunity_assessment a ON a.opp_id=o.id WHERE o.org_id=? OR o.id=?", (focus, focus))
    else:
        opps = rows(c, "SELECT o.id, o.name, o.org_id, o.org_name, o.type_canonical, a.status, a.fit FROM opportunity o"
                       " JOIN opportunity_assessment a ON a.opp_id=o.id WHERE a.status IN"
                       " ('eligible_likely','needs_check','travel_or_relocation','eligible_later')"
                       " ORDER BY a.fit DESC LIMIT ?", (limit,))
    for o in opps:
        node(o["id"], o["name"], "opportunity", type=o["type_canonical"], eligibility=o["status"], fit=o["fit"])
        if o["org_id"]:
            node(o["org_id"], o["org_name"], "organization")
            edges.append({"source": o["id"], "target": o["org_id"], "rel": "offered_by"})
    org_ids = [n for n, v in nodes.items() if v["kind"] == "organization"]
    if org_ids:
        for e in rows(c, "SELECT * FROM edge WHERE rel='part_of' AND src_id IN (%s)" % ",".join("?" * len(org_ids)),
                      org_ids):
            par = one(c, "SELECT name FROM organization WHERE id=?", (e["dst_id"],))
            node(e["dst_id"], par["name"] if par else e["dst_id"], "organization")
            edges.append({"source": e["src_id"], "target": e["dst_id"], "rel": "part_of"})
    for t in rows(c, "SELECT id, entity, contact, org_id, person_id, ask FROM outreach_target ORDER BY priority LIMIT 40"):
        node(t["org_id"], t["entity"], "organization")
        if t["person_id"]:
            node(t["person_id"], t["contact"], "person")
            edges.append({"source": t["person_id"], "target": t["org_id"], "rel": "works_at"})
        node(t["id"], f"Outreach: {t['ask'][:40] if t['ask'] else t['entity']}", "outreach")
        edges.append({"source": t["id"], "target": t["org_id"], "rel": "targets"})
    for h in rows(c, "SELECT id, target_org, classification FROM hypothesis"):
        oid = "ORG-" + __import__("hashlib").sha1(h["target_org"].strip().lower().encode()).hexdigest()[:10]
        node(oid, h["target_org"], "organization")
        node(h["id"], f"Hypothesis: {h['target_org']}", "hypothesis", classification=h["classification"])
        edges.append({"source": h["id"], "target": oid, "rel": "proposes_to", "inferred": True})
    return _json({"nodes": list(nodes.values()), "edges": edges})


# ------------------------------------------------------------------ profile / parameters / objectives
@app.get("/api/profile")
def get_profile():
    c = con()
    return _json({"items": S.profile(c), "facts": S.profile_facts(c),
                  "revisions": rows(c, "SELECT * FROM revision ORDER BY id DESC LIMIT 30")})


@app.patch("/api/profile/{item_id}")
def patch_profile(item_id: str, body: dict = Body(...)):
    try:
        return _json(S.update_profile_item(con(), item_id, body))
    except KeyError:
        raise HTTPException(404)


@app.post("/api/profile")
def add_profile(body: dict = Body(...)):
    return _json(S.add_profile_item(con(), body["dimension"], body["key"], body.get("label", body["key"]),
                                    body.get("value"), body.get("evidence_status", "user-supplied")))


@app.post("/api/undo")
def undo():
    r = S.undo_last(con())
    return _json({"undone": r})


@app.get("/api/parameters")
def get_parameters():
    c = con()
    return _json({"parameters": S.parameters(c),
                  "history": rows(c, "SELECT * FROM parameter_history ORDER BY id DESC LIMIT 50")})


@app.patch("/api/parameters/{name}")
def patch_parameter(name: str, body: dict = Body(...)):
    try:
        return _json(S.update_parameter(con(), name, body.get("dist"), body.get("origin"), body.get("notes"),
                                        body.get("reason", "user edit")))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/objectives")
def get_objectives():
    c = con()
    return _json({"profiles": S.objectives(c), "defaults": get_meta(c, "objective_defaults", {})})


@app.put("/api/objectives")
def put_objective(body: dict = Body(...)):
    return _json(S.save_objective(con(), body))


@app.get("/api/strategies")
def get_strategies():
    return _json(S.strategies(con()))


@app.put("/api/strategies")
def put_strategy(body: dict = Body(...)):
    try:
        return _json(S.save_strategy(con(), body))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/strategies/{sid}")
def delete_strategy(sid: str):
    c = con()
    with tx(c):
        c.execute("DELETE FROM strategy WHERE id=? AND origin<>'preset'", (sid,))
    return {"ok": True}


# ------------------------------------------------------------------ model
@app.get("/api/model")
def get_model():
    c = con()
    m = S.build_model(c)
    acts = [a.describe() for a in m.actions]
    # unlock graph: action -> token (effects/outcomes) -> action (requires / shifts)
    produces, consumes = [], []
    for a in m.actions:
        toks = set((a.effects.get("tokens") or {}).keys())
        for s in a.stages:
            for o in s.outcomes:
                toks |= set(o.tokens)
                if "offer" in o.metrics:
                    produces.append({"action": a.id, "token": "offer:" + o.metrics["offer"], "via": o.label})
                for sh in (o.p.shifts if o.p else []):
                    if "token" in sh:
                        consumes.append({"action": a.id, "token": sh["token"], "kind": "raises_odds", "param": sh["param"]})
        for t in toks:
            produces.append({"action": a.id, "token": t})
        def walk(cnd):
            if not cnd:
                return
            if "token" in cnd:
                consumes.append({"action": a.id, "token": cnd["token"], "kind": "requires"})
            for k in ("all", "any"):
                for x in cnd.get(k, []):
                    walk(x)
            if "not" in cnd:
                walk(cnd["not"])
        walk(a.requires_spec)
    return _json({"version": m.version, "fingerprint": m.fingerprint(), "start": m.start.isoformat(),
                  "horizon_weeks": m.horizon_weeks, "graduation_week": m.graduation_week, "actions": acts,
                  "offer_classes": m.offer_classes, "initial_tokens": m.initial_tokens,
                  "unlocks": {"produces": produces, "consumes": consumes}})


# ------------------------------------------------------------------ simulation
@app.post("/api/simulate")
def simulate(body: dict = Body(default={})):
    with _lock:
        try:
            r = S.run_simulation(con(), strategy_ids=body.get("strategies"), scenario=body.get("scenario"),
                                 objective_id=body.get("objective", "balanced"),
                                 n_worlds=int(min(max(body.get("n_worlds", 2000), 100), 20000)),
                                 seed=int(body.get("seed", 20261009)), label=body.get("label"),
                                 extra_strategies=body.get("extra_strategies"), voi=body.get("voi", True))
        except (ValueError, KeyError) as e:
            raise HTTPException(400, str(e))
    return _json(r)


@app.get("/api/runs")
def runs():
    return _json(S.list_runs(con()))


@app.get("/api/runs/{rid}")
def run(rid: str):
    r = S.get_run(con(), rid)
    if not r:
        raise HTTPException(404)
    return _json(r)


@app.post("/api/runs/{rid}/reanalyze")
def reanalyze(rid: str, body: dict = Body(...)):
    try:
        return _json(S.reanalyze(con(), rid, body["objective"]))
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/api/compare-scenarios")
def compare_scenarios(body: dict = Body(default={})):
    from .analysis_jobs import scenario_regret
    with _lock:
        return _json(scenario_regret(con(), body.get("strategies"), body.get("objective", "balanced"),
                                     int(body.get("n_worlds", 1500)), body.get("scenarios")))


@app.post("/api/tornado")
def tornado(body: dict = Body(default={})):
    from .analysis_jobs import tornado as tor
    with _lock:
        return _json(tor(con(), body.get("strategies"), body.get("objective", "balanced"),
                         int(body.get("n_worlds", 1200)), body.get("params"), body.get("scenario")))


@app.post("/api/strategy-search")
def strategy_search(body: dict = Body(default={})):
    from .strategy_search import search_strategies
    with _lock:
        return _json(search_strategies(con(), body.get("objective", "balanced"), body.get("scenario"),
                                       int(body.get("generations", 8)), int(body.get("population", 24)),
                                       int(body.get("n_worlds", 500)), int(body.get("seed", 7))))


# ------------------------------------------------------------------ research, hypotheses, events
@app.get("/api/research")
def research():
    c = con()
    ledger = (ROOT / "docs" / "RESEARCH_LEDGER.md")
    return _json({
        "search_gaps": rows(c, "SELECT * FROM search_gap"),
        "research_log": rows(c, "SELECT * FROM research_log ORDER BY created_at DESC"),
        "claims_by_grade": rows(c, "SELECT evidence_grade, verification_method, COUNT(*) n FROM claim GROUP BY 1,2"),
        "contradictions": rows(c, "SELECT * FROM claim WHERE status IN ('contradicted','superseded') ORDER BY recorded_at DESC LIMIT 200"),
        "agent_claims": rows(c, "SELECT c.*, s.url AS source_url FROM claim c LEFT JOIN source s ON s.id=c.source_id"
                                " WHERE c.recorded_by LIKE 'agent:%' ORDER BY c.recorded_at DESC LIMIT 400"),
        "ledger_md": ledger.read_text() if ledger.exists() else None,
    })


@app.get("/api/hypotheses")
def hypotheses():
    c = con()
    out = rows(c, "SELECT * FROM hypothesis ORDER BY id")
    for h in out:
        h["evidence"] = json.loads(h.pop("evidence_json") or "[]")
        h["invalidators"] = json.loads(h.pop("invalidators_json") or "[]")
    return _json(out)


@app.get("/api/outreach")
def outreach():
    return _json(rows(con(), "SELECT * FROM outreach_target ORDER BY priority"))


@app.get("/api/events")
def events():
    return _json(rows(con(), "SELECT * FROM event ORDER BY starts_on IS NULL, starts_on"))


@app.get("/api/docs/{name}")
def doc(name: str):
    p = ROOT / "docs" / f"{name}.md"
    if not p.exists() or "/" in name:
        raise HTTPException(404)
    return PlainTextResponse(p.read_text())


# ------------------------------------------------------------------ execution + calibration
@app.get("/api/actions")
def list_actions():
    return _json(rows(con(), "SELECT * FROM action_item ORDER BY CASE status WHEN 'todo' THEN 0 WHEN 'doing' THEN 1"
                             " ELSE 2 END, due"))


@app.post("/api/actions")
def add_action(body: dict = Body(...)):
    from .execution import upsert_action
    return _json(upsert_action(con(), body))


@app.patch("/api/actions/{aid}")
def patch_action(aid: str, body: dict = Body(...)):
    from .execution import upsert_action
    return _json(upsert_action(con(), {**body, "id": aid}))


@app.post("/api/plan/generate")
def generate_plan(body: dict = Body(default={})):
    from .execution import generate_plan as gp
    return _json(gp(con(), body.get("run_id"), body.get("strategy")))


@app.post("/api/plan/schedule")
def plan_schedule(body: dict = Body(default={})):
    from .schedule import plan_days
    return _json(plan_days(con(), int(body.get("days", 14)), float(body.get("weekday_hours", 5)),
                           float(body.get("weekend_hours", 9)), int(body.get("max_tasks_per_day", 2))))


@app.post("/api/outcomes")
def log_outcome(body: dict = Body(...)):
    from .execution import record_outcome
    try:
        return _json(record_outcome(con(), body))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/outcomes")
def outcomes():
    return _json(rows(con(), "SELECT * FROM outcome ORDER BY recorded_at DESC"))


@app.get("/api/forecasts")
def forecasts():
    from .execution import forecast_scores
    c = con()
    return _json({"forecasts": rows(c, "SELECT * FROM forecast ORDER BY created_at DESC"), "scores": forecast_scores(c)})


@app.post("/api/forecasts")
def add_forecast(body: dict = Body(...)):
    from .execution import upsert_forecast
    return _json(upsert_forecast(con(), body))


# ------------------------------------------------------------------ theater
@app.get("/api/theater/worlds")
def theater_worlds(run: str, strategy: str):
    from .theater import worlds_summary
    r = S.get_run(con(), run)
    if not r or strategy not in r["strategy_results"]:
        raise HTTPException(404)
    return _json(worlds_summary(r, strategy))


@app.get("/api/theater/spec")
def theater_spec(run: str, strategy: str, world: int = 0):
    from .theater import build_spec
    try:
        return _json(build_spec(con(), run, strategy, world))
    except KeyError as e:
        raise HTTPException(404, str(e))


# ------------------------------------------------------------------ media
@app.get("/api/media")
def media_list():
    return _json(rows(con(), "SELECT * FROM media ORDER BY created_at DESC"))


@app.post("/api/media/render")
def media_render(body: dict = Body(...)):
    from .media import start_render
    return _json(start_render(con(), body))


@app.get("/api/media/{mid}/spec")
def media_spec(mid: str):
    r = one(con(), "SELECT spec_json FROM media WHERE id=?", (mid,))
    if not r:
        raise HTTPException(404)
    return _json(json.loads(r["spec_json"]))


@app.get("/media/{path:path}")
def media_file(path: str):
    p = (ROOT / "media" / "renders" / path).resolve()
    if not str(p).startswith(str((ROOT / "media" / "renders").resolve())) or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ------------------------------------------------------------------ export
@app.get("/api/export/{kind}")
def export(kind: str):
    c = con()
    if kind == "opportunities.csv":
        items = rows(c, "SELECT o.id, o.name, o.org_name, o.type_canonical, o.access_class, o.deadline_utc,"
                        " o.deadline_quality, o.official_url, a.status AS eligibility, a.reasons_json, a.fit,"
                        " o.confidence, o.verification_result, o.origin FROM opportunity o"
                        " LEFT JOIN opportunity_assessment a ON a.opp_id=o.id ORDER BY o.deadline_utc")
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(items[0].keys()))
        w.writeheader()
        w.writerows(items)
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=horizon_opportunities.csv"})
    if kind == "claims.json":
        return _json(rows(c, "SELECT * FROM claim"))
    if kind == "actions.json":
        return _json(rows(c, "SELECT * FROM action_item"))
    if kind.startswith("run-") and kind.endswith(".json"):
        r = S.get_run(c, kind[4:-5])
        if not r:
            raise HTTPException(404)
        return Response(json.dumps(r, default=S._np, indent=1), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={kind}"})
    if kind == "backup.sqlite3":
        dest = ROOT / "data" / "backups"
        dest.mkdir(parents=True, exist_ok=True)
        p = dest / f"horizon-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3"
        c.execute(f"VACUUM INTO '{p}'")
        return FileResponse(p, filename=p.name)
    raise HTTPException(404)


# ------------------------------------------------------------------ frontend
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.exists() and f.is_file():
            return FileResponse(f)
        # index.html must never be cached: it names the current hashed bundles
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
