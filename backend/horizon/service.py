"""Application services: seeding, profile, parameters, model assembly, simulation runs."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from . import eligibility, search
from .db import ROOT, get_meta, now_iso, one, record_revision, rows, set_meta, tx
from .ingest import import_all
from .sim import analysis as A
from .sim.engine import REPORT_METRICS, Scenario, Simulator, Strategy
from .sim.model import Model, load_model
from .sim.params import Dist, Param

SEED = ROOT / "data" / "seed"
RUNS = ROOT / "data" / "runs"
CATALOG = SEED / "actions.yaml"


# ------------------------------------------------------------------ bootstrap
def bootstrap(con: sqlite3.Connection, embed: bool = True) -> dict:
    out = {}
    if not one(con, "SELECT 1 AS x FROM opportunity LIMIT 1"):
        out["import"] = import_all(con)
    with tx(con):
        if not one(con, "SELECT 1 AS x FROM profile_item LIMIT 1"):
            seed_profile(con)
            out["profile"] = "seeded"
        if not one(con, "SELECT 1 AS x FROM parameter LIMIT 1"):
            seed_parameters(con)
            out["parameters"] = "seeded"
        if not one(con, "SELECT 1 AS x FROM objective_profile LIMIT 1"):
            seed_objectives(con)
        if not one(con, "SELECT 1 AS x FROM strategy LIMIT 1"):
            seed_strategies(con)
    if not one(con, "SELECT 1 AS x FROM doc_fts LIMIT 1"):
        out["index"] = search.build_index(con, embed=embed)
    if not one(con, "SELECT 1 AS x FROM opportunity_assessment LIMIT 1"):
        out["assessed"] = assess_all(con)
    return out


def seed_profile(con):
    data = yaml.safe_load((SEED / "profile.yaml").read_text())
    for dim, items in data.items():
        for it in items:
            con.execute("INSERT OR REPLACE INTO profile_item(id, dimension, key, label, value, evidence_status,"
                        " source_ref, notes, editable, updated_at) VALUES(?,?,?,?,?,?,?,?,1,?)",
                        (f"{dim}.{it['key']}", dim, it["key"], it.get("label"), None if it.get("value") is None
                         else str(it["value"]), it.get("evidence_status", "unknown"), it.get("source_ref"),
                         it.get("notes"), now_iso()))


def seed_parameters(con, path: Path | None = None):
    raw = yaml.safe_load((path or SEED / "parameters.yaml").read_text())
    for name, d in raw.items():
        Dist.parse(d["dist"])
        con.execute("INSERT OR REPLACE INTO parameter(id, name, description, unit, dist, params_json, origin,"
                    " sources_json, evidence_grade, transferability, notes, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (name, name, d.get("description"), d.get("unit"), d["dist"], json.dumps({}), d["origin"],
                     json.dumps(d.get("sources", [])), d.get("evidence_grade"), d.get("transferability"),
                     d.get("notes"), now_iso()))


def seed_objectives(con):
    data = yaml.safe_load((SEED / "objectives.yaml").read_text())
    set_meta(con, "objective_defaults", data["defaults"])
    for p in data["profiles"]:
        con.execute("INSERT OR REPLACE INTO objective_profile VALUES(?,?,?,?,1,?)",
                    (p["id"], p["name"], p.get("description"), json.dumps(p), now_iso()))


def seed_strategies(con):
    for s in yaml.safe_load((SEED / "strategies.yaml").read_text()):
        con.execute("INSERT OR REPLACE INTO strategy VALUES(?,?,?,?,?,?,?)",
                    (s["id"], s["name"], s.get("description"), json.dumps(s), "preset", now_iso(), now_iso()))


# ------------------------------------------------------------------ profile
def profile(con) -> list[dict]:
    return rows(con, "SELECT * FROM profile_item ORDER BY dimension, rowid")


def profile_facts(con) -> dict:
    f = {r["key"]: r["value"] for r in profile(con)}
    return {
        "graduation": f.get("graduation"), "citizenship": (f.get("citizenship") or "unknown"),
        "relocation": (f.get("relocation") or "").strip().lower() or None,
    }


def update_profile_item(con, item_id: str, fields: dict) -> dict:
    before = one(con, "SELECT * FROM profile_item WHERE id=?", (item_id,))
    if not before:
        raise KeyError(item_id)
    allowed = {k: v for k, v in fields.items() if k in ("value", "evidence_status", "notes", "label")}
    with tx(con):
        for k, v in allowed.items():
            con.execute(f"UPDATE profile_item SET {k}=?, updated_at=? WHERE id=?", (v, now_iso(), item_id))
        after = one(con, "SELECT * FROM profile_item WHERE id=?", (item_id,))
        record_revision(con, "profile_item", item_id, before, after)
    assess_all(con)
    return after


def add_profile_item(con, dimension: str, key: str, label: str, value: str | None, evidence_status: str) -> dict:
    iid = f"{dimension}.{key}"
    with tx(con):
        con.execute("INSERT INTO profile_item(id, dimension, key, label, value, evidence_status, editable, updated_at)"
                    " VALUES(?,?,?,?,?,?,1,?)", (iid, dimension, key, label, value, evidence_status, now_iso()))
        record_revision(con, "profile_item", iid, None, {"label": label, "value": value})
    return one(con, "SELECT * FROM profile_item WHERE id=?", (iid,))


def undo_last(con) -> dict | None:
    rev = one(con, "SELECT * FROM revision WHERE undone=0 ORDER BY id DESC LIMIT 1")
    if not rev:
        return None
    before = json.loads(rev["before_json"]) if rev["before_json"] else None
    table, rid = rev["table_name"], rev["row_id"]
    with tx(con):
        if table == "profile_item":
            if before is None:
                con.execute("DELETE FROM profile_item WHERE id=?", (rid,))
            else:
                for k in ("value", "evidence_status", "notes", "label"):
                    con.execute(f"UPDATE profile_item SET {k}=? WHERE id=?", (before.get(k), rid))
        elif table == "parameter":
            if before:
                con.execute("UPDATE parameter SET dist=?, origin=?, notes=? WHERE name=?",
                            (before["dist"], before["origin"], before.get("notes"), rid))
        elif table == "strategy":
            if before is None:
                con.execute("DELETE FROM strategy WHERE id=?", (rid,))
            else:
                con.execute("INSERT OR REPLACE INTO strategy VALUES(?,?,?,?,?,?,?)",
                            (before["id"], before["name"], before.get("description"), before["spec_json"],
                             before.get("origin"), before.get("created_at"), now_iso()))
        elif table == "shortlist":
            if before is None:
                con.execute("DELETE FROM shortlist WHERE opp_id=?", (rid,))
            else:
                con.execute("INSERT OR REPLACE INTO shortlist VALUES(?,?,?,?)",
                            (rid, before.get("added_at"), before.get("note"), before.get("origin")))
        con.execute("UPDATE revision SET undone=1 WHERE id=?", (rev["id"],))
    if table == "profile_item":
        assess_all(con)
    return rev


# ------------------------------------------------------------------ eligibility + fit
def _profile_vec(con):
    f = {r["key"]: r["value"] for r in profile(con)}
    text = ("AI research engineer. " + (f.get("interests") or "") + ". Evaluation benchmarks, agent systems, "
            "world models, ARC-AGI, multilingual Indic NLP and machine translation, efficient inference.")
    return text


def assess_all(con) -> int:
    facts = profile_facts(con)
    ph = hashlib.sha1(json.dumps(facts, sort_keys=True).encode()).hexdigest()[:10]
    now = datetime.now(timezone.utc)
    fits: dict[str, float] = {}
    try:
        M, keys = search._matrix(con)
        if len(keys):
            qv = np.asarray(list(search._embedder().query_embed([_profile_vec(con)]))[0], dtype=np.float32)
            qv /= np.linalg.norm(qv)
            s = M @ qv
            fits = {k[1]: float(v) for k, v in zip(keys, s) if k[0] == "opportunity"}
    except Exception:  # embeddings optional
        fits = {}
    opps = rows(con, "SELECT * FROM opportunity")
    with tx(con):
        con.execute("DELETE FROM opportunity_assessment")
        for o in opps:
            st, reasons = eligibility.assess(o, facts, now)
            con.execute("INSERT INTO opportunity_assessment VALUES(?,?,?,?,?,?)",
                        (o["id"], st, json.dumps(reasons), fits.get(o["id"]), ph, now_iso()))
    return len(opps)


# ------------------------------------------------------------------ parameters
def param_defs(con) -> dict[str, Param]:
    out = {}
    for r in rows(con, "SELECT * FROM parameter"):
        out[r["name"]] = Param(name=r["name"], dist=Dist.parse(r["dist"]), origin=r["origin"],
                               description=r["description"] or "", notes=r["notes"] or "",
                               sources=json.loads(r["sources_json"] or "[]"), evidence_grade=r["evidence_grade"])
    return out


def parameters(con) -> list[dict]:
    out = []
    for r in rows(con, "SELECT * FROM parameter ORDER BY name"):
        d = Dist.parse(r["dist"])
        r["mean"] = d.mean()
        r["p10"], r["p90"] = d.quantile(0.1), d.quantile(0.9)
        r["sources"] = json.loads(r.pop("sources_json") or "[]")
        out.append(r)
    return out


def update_parameter(con, name: str, dist: str | None = None, origin: str | None = None, notes: str | None = None,
                     reason: str = "user edit") -> dict:
    before = one(con, "SELECT * FROM parameter WHERE name=?", (name,))
    if not before:
        raise KeyError(name)
    if dist:
        Dist.parse(dist)
    with tx(con):
        con.execute("UPDATE parameter SET dist=COALESCE(?, dist), origin=COALESCE(?, origin), notes=COALESCE(?, notes),"
                    " updated_at=? WHERE name=?", (dist, origin, notes, now_iso(), name))
        after = one(con, "SELECT * FROM parameter WHERE name=?", (name,))
        con.execute("INSERT INTO parameter_history(param_id, changed_at, before_json, after_json, reason)"
                    " VALUES(?,?,?,?,?)", (name, now_iso(), json.dumps(before), json.dumps(after), reason))
        record_revision(con, "parameter", name, before, after)
    return after


# ------------------------------------------------------------------ model assembly
def shortlist(con) -> list[dict]:
    return rows(con, "SELECT s.*, o.name, o.type_canonical, o.deadline_utc, a.status AS eligibility FROM shortlist s"
                     " JOIN opportunity o ON o.id = s.opp_id LEFT JOIN opportunity_assessment a ON a.opp_id = s.opp_id"
                     " ORDER BY o.deadline_utc")


def set_shortlist(con, opp_id: str, on: bool, note: str | None = None):
    before = one(con, "SELECT * FROM shortlist WHERE opp_id=?", (opp_id,))
    with tx(con):
        if on:
            con.execute("INSERT OR REPLACE INTO shortlist VALUES(?,?,?,?)", (opp_id, now_iso(), note, "user"))
        else:
            con.execute("DELETE FROM shortlist WHERE opp_id=?", (opp_id,))
        record_revision(con, "shortlist", opp_id, before, one(con, "SELECT * FROM shortlist WHERE opp_id=?", (opp_id,)))


def opportunity_actions(con) -> list[dict]:
    """Turn shortlisted opportunities into simulator actions using the type templates."""
    cat = yaml.safe_load(CATALOG.read_text())
    templates = cat.get("templates", {})
    out = []
    now = datetime.now(timezone.utc)
    for s in shortlist(con):
        o = one(con, "SELECT * FROM opportunity WHERE id=?", (s["opp_id"],))
        tpl = templates.get(o["type_canonical"])
        if not tpl:
            continue
        dl = o["deadline_utc"]
        if dl and datetime.fromisoformat(dl) < now:
            continue
        outcome = {"label": "Selected / placed",
                   "p": {"base": tpl["base"],
                         "shifts": [{"param": "bonus_preprint", "token": "public_outputs", "cap": 2},
                                    {"param": "bonus_referral", "token": "referrals", "cap": 1},
                                    {"param": "bonus_peer_reviewed", "token": "peer_reviewed", "cap": 1}],
                         "factors": {"portfolio": "load_portfolio"}},
                   "tokens": {f"won_{o['id']}": 1}, "metrics": {"ties": 1}}
        if tpl.get("offer"):
            outcome["metrics"]["offer"] = tpl["offer"]
        elif o["type_canonical"] in ("hackathon", "competition"):
            outcome["metrics"]["cash_lpa"] = "prize_hackathon_lpa"
            outcome["tokens"]["hackathon_wins"] = 1
        act = {"id": f"opp_{o['id']}", "name": f"Apply: {o['name']}", "kind": "application",
               "effort": tpl["effort"], "automatable": tpl.get("automatable", 0.3),
               "deadline": dl, "deadline_basis": f"sheet ({o['deadline_quality']})" if dl else None,
               "opportunity_id": o["id"], "template": o["type_canonical"],
               "stages": [{"name": "Selection", "delay": "delay_app_response", "outcomes": [outcome],
                           "otherwise": {"label": "Not selected"}}]}
        out.append(act)
    return out


def build_model(con) -> Model:
    return load_model(CATALOG, param_defs(con), extra_actions=opportunity_actions(con))


def strategies(con) -> list[dict]:
    out = []
    for r in rows(con, "SELECT * FROM strategy ORDER BY origin DESC, created_at"):
        d = json.loads(r["spec_json"])
        d.update({"origin": r["origin"], "updated_at": r["updated_at"]})
        out.append(d)
    return out


def save_strategy(con, spec: dict, origin: str = "user") -> dict:
    spec = dict(spec)
    spec.setdefault("id", "usr_" + uuid.uuid4().hex[:8])
    Strategy.from_dict(spec)  # validates shape
    before = one(con, "SELECT * FROM strategy WHERE id=?", (spec["id"],))
    with tx(con):
        con.execute("INSERT OR REPLACE INTO strategy VALUES(?,?,?,?,?,?,?)",
                    (spec["id"], spec.get("name", spec["id"]), spec.get("description"), json.dumps(spec),
                     origin if not before else before["origin"], before["created_at"] if before else now_iso(),
                     now_iso()))
        record_revision(con, "strategy", spec["id"], before, spec)
    return spec


def objectives(con) -> list[dict]:
    return [json.loads(r["config_json"]) | {"builtin": bool(r["builtin"])}
            for r in rows(con, "SELECT * FROM objective_profile ORDER BY builtin DESC, rowid")]


def save_objective(con, prof: dict) -> dict:
    prof = dict(prof)
    prof.setdefault("id", "obj_" + uuid.uuid4().hex[:8])
    with tx(con):
        con.execute("INSERT OR REPLACE INTO objective_profile VALUES(?,?,?,?,0,?)",
                    (prof["id"], prof.get("name", prof["id"]), prof.get("description"), json.dumps(prof), now_iso()))
    return prof


def objective(con, oid: str) -> dict:
    r = one(con, "SELECT config_json FROM objective_profile WHERE id=?", (oid,))
    if not r:
        raise KeyError(oid)
    return json.loads(r["config_json"])


# ------------------------------------------------------------------ simulation runs
SCENARIO_FIELDS = ("weekly_hours", "ai_multiplier", "effort_bias", "sustainable_cap", "switch_cost", "focus_k",
                   "factor_corr", "independent_outcomes", "allow_relocation", "param_overrides", "academic",
                   "effort_overrides")


def make_scenario(spec: dict | None) -> Scenario:
    spec = dict(spec or {})
    base = Scenario.preset(spec.pop("preset", "central"))
    for k, v in spec.items():
        if k in SCENARIO_FIELDS and v is not None:
            setattr(base, k, v)
    if "name" in spec:
        base.name = spec["name"]
    return base


def _strategy_objs(con, ids: list[str] | None, extra: list[dict] | None = None) -> list[Strategy]:
    all_s = {s["id"]: s for s in strategies(con)}
    for e in extra or []:
        all_s[e["id"]] = e
    ids = ids or list(all_s)
    return [Strategy.from_dict(all_s[i]) for i in ids if i in all_s]


def run_simulation(con, strategy_ids: list[str] | None = None, scenario: dict | None = None,
                   objective_id: str = "balanced", n_worlds: int = 2000, seed: int = 20261009,
                   label: str | None = None, extra_strategies: list[dict] | None = None,
                   voi: bool = True, n_trace: int = 24) -> dict:
    t0 = time.time()
    model = build_model(con)
    sc = make_scenario(scenario)
    strats = _strategy_objs(con, strategy_ids, extra_strategies)
    if not strats:
        raise ValueError("no strategies selected")
    sim = Simulator(model, sc, n_worlds=n_worlds, seed=seed, n_trace=n_trace)
    results = {s.id: sim.run(s) for s in strats}
    defaults = get_meta(con, "objective_defaults", {})
    prof = objective(con, objective_id)
    rid = "RUN-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    analysis = analyze(results, sim, prof, defaults, voi=voi)
    warnings = run_warnings(model, results, analysis)
    payload = {
        "id": rid, "label": label, "created_at": now_iso(), "model_version": model.version,
        "model_fingerprint": model.fingerprint(), "dataset_version": get_meta(con, "dataset_version"),
        "seed": seed, "n_worlds": n_worlds, "horizon_weeks": sim.T, "algorithm":
            "Vectorized discrete-time Monte Carlo over an AND/OR action graph; Beta/LogNormal epistemic draws per "
            "world; Gaussian latent factors; common random numbers across strategies",
        "scenario": {k: getattr(sc, k) for k in ("name",) + SCENARIO_FIELDS},
        "objective": prof, "strategies": [s.to_dict() for s in strats],
        "start_date": model.start.date().isoformat(), "graduation_week": model.graduation_week,
        "strategy_results": {sid: compact_result(r, model) for sid, r in results.items()},
        "analysis": analysis, "warnings": warnings, "limitations": LIMITATIONS,
        "parameters_used": {k: {"dist": str(p.dist), "origin": p.origin} for k, p in model.params.items()},
        "actions": {a.id: {"name": a.name, "kind": a.kind, "deadline": a.deadline_iso,
                           "deadline_week": a.deadline_week, "deadline_basis": a.deadline_basis,
                           "opportunity_id": a.opportunity_id} for a in model.actions},
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    arc = RUNS / f"{rid}.npz"
    arrays = {}
    for sid, r in results.items():
        for k, v in r["metrics"].items():
            arrays[f"m::{sid}::{k}"] = v.astype(np.float32)
    for k, v in sim.P.drawn.items():
        arrays[f"p::{k}"] = np.asarray(v, dtype=np.float32)
    for f, v in sim.z.items():
        arrays[f"z::{f}"] = v.astype(np.float32)
    np.savez_compressed(arc, **arrays)
    dur = int((time.time() - t0) * 1000)
    payload["duration_ms"] = dur
    with tx(con):
        con.execute("INSERT INTO sim_run(id, created_at, label, model_version, dataset_version, seed, scenario_json,"
                    " objective_id, strategies_json, params_json, algorithm, n_worlds, horizon_weeks, diagnostics_json,"
                    " results_json, warnings_json, limitations_json, duration_ms, archive_path, status)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (rid, payload["created_at"], label, model.version + " / " + payload["model_fingerprint"],
                     payload["dataset_version"], seed, json.dumps(payload["scenario"]), objective_id,
                     json.dumps(payload["strategies"]), json.dumps(payload["parameters_used"]), payload["algorithm"],
                     n_worlds, sim.T, json.dumps(analysis.get("convergence")), json.dumps(payload, default=_np),
                     json.dumps(warnings), json.dumps(LIMITATIONS), dur, str(arc.relative_to(ROOT)), "done"))
    return payload


def _np(o):
    if isinstance(o, np.generic):
        v = o.item()
        return None if isinstance(v, float) and (math.isinf(v) or math.isnan(v)) else v
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return None
    raise TypeError(type(o))


def compact_result(r: dict, model: Model) -> dict:
    return {
        "metrics": {k: A.summarize(v) | {"hist": A.histogram(v)} for k, v in r["metrics"].items()},
        "series": r["series"], "offer_series": r["offer_series"],
        "offers": {c: float(v.mean()) for c, v in r["offers"].items()},
        "action_stats": r["action_stats"], "trace": r["trace"], "unknown_actions": r["unknown_actions"],
    }


def analyze(results: dict, sim: Simulator, prof: dict, defaults: dict, voi: bool = True) -> dict:
    ev = A.evaluate(results, prof, defaults)
    U = ev.pop("utilities")
    means = {sid: {k: float(np.mean(v)) for k, v in r["metrics"].items()} for sid, r in results.items()}
    pareto_metrics = ["peer_reviewed", "best_comp_lpa", "position_by_grad", "optionality", "autonomy",
                      "founder_stage", "crunch_weeks"]
    out = {
        "objective_id": prof.get("id"), "ranking": ev["ranking"], "top_vs_runner_up": ev["top_vs_runner_up"],
        "dominance": A.dominance_matrix(U), "means": means,
        "pareto": {"metrics": pareto_metrics, "front": A.pareto_front(means, pareto_metrics)},
        "utility_hist": {sid: A.histogram(u, 30) for sid, u in U.items()},
        "convergence": {sid: A.convergence(u) for sid, u in U.items()},
    }
    if voi and len(U) >= 2:
        theta = {k: v for k, v in sim.P.drawn.items() if not k.startswith("inline:") and not np.allclose(v, v[0])}
        vois = []
        for k, th in theta.items():
            e = A.evppi(U, th, n_perm=12)
            p = sim.m.params.get(k)
            vois.append({"param": k, "origin": p.origin if p else "inline", "description": p.description if p else "",
                         **{kk: e[kk] for kk in ("evppi", "evppi_raw", "noise_floor", "floor_p95",
                                                  "decision_sensitive", "best_by_bin")}})
        vois.sort(key=lambda r: -r["evppi"])
        best = ev["ranking"][0]["strategy"]
        out["voi"] = vois
        out["sensitivity"] = A.global_sensitivity(U[best], theta)[:15]
        out["sensitivity_strategy"] = best
    return out


LIMITATIONS = [
    "Simulated trajectories are conditional on the model's structure and parameters; they are not predictions.",
    "Most selection probabilities are expert judgment or placeholders until replaced by published base rates or "
    "the user's own outcomes; check each parameter's origin before trusting a ranking.",
    "Evidence effects (preprint, referral, peer-reviewed paper) are causal assumptions with wide uncertainty, "
    "not identified causal estimates.",
    "Unadvertised and created opportunities appear only through the curated outreach and collaboration actions; "
    "opportunities nobody has written down are outside the model.",
    "Compensation figures are illustrative placeholders unless the parameter origin says otherwise.",
    "The academic calendar is a placeholder; edit it to the real institutional calendar.",
]


def run_warnings(model: Model, results: dict, analysis: dict) -> list[str]:
    w = []
    weak = [k for k, p in model.params.items() if p.origin in ("illustrative_placeholder", "unknown")]
    if weak:
        w.append(f"{len(weak)} parameters are placeholders or unknown: {', '.join(sorted(weak)[:8])}"
                 + ("…" if len(weak) > 8 else ""))
    assumed = [a.id for a in model.actions if a.deadline_basis == "assumed"]
    if assumed:
        w.append(f"{len(assumed)} action deadlines are assumed, not verified: {', '.join(assumed)}")
    t = analysis.get("top_vs_runner_up")
    if t and not t["resolved"]:
        w.append(f"Top two strategies are not separated by Monte Carlo error (z = {t['z']:.1f}); "
                 "treat them as tied or increase the number of worlds.")
    for sid, r in results.items():
        if r["unknown_actions"]:
            w.append(f"Strategy {sid} references unknown actions: {r['unknown_actions']}")
    return w


def get_run(con, rid: str) -> dict | None:
    r = one(con, "SELECT results_json FROM sim_run WHERE id=?", (rid,))
    return json.loads(r["results_json"]) if r else None


def list_runs(con, limit: int = 50) -> list[dict]:
    return rows(con, "SELECT id, created_at, label, model_version, dataset_version, seed, objective_id, n_worlds,"
                     " duration_ms, scenario_json, strategies_json FROM sim_run ORDER BY created_at DESC LIMIT ?",
                (limit,))


def reanalyze(con, rid: str, objective_id: str) -> dict:
    """Re-rank an archived run under a different value model without re-simulating."""
    run = get_run(con, rid)
    if not run:
        raise KeyError(rid)
    arc = np.load(ROOT / one(con, "SELECT archive_path FROM sim_run WHERE id=?", (rid,))["archive_path"])
    results: dict[str, dict] = {}
    for key in arc.files:
        if key.startswith("m::"):
            _, sid, metric = key.split("::")
            results.setdefault(sid, {"metrics": {}})["metrics"][metric] = arc[key].astype(float)
    prof = objective(con, objective_id)
    ev = A.evaluate(results, prof, get_meta(con, "objective_defaults", {}))
    U = ev.pop("utilities")
    return {"run_id": rid, "objective_id": objective_id, "ranking": ev["ranking"],
            "top_vs_runner_up": ev["top_vs_runner_up"], "dominance": A.dominance_matrix(U),
            "utility_hist": {sid: A.histogram(u, 30) for sid, u in U.items()}}
