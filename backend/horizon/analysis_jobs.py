"""Heavier analyses that re-run the simulator: scenario regret and one-at-a-time sensitivity."""
from __future__ import annotations

import numpy as np

from . import service as S
from .db import get_meta
from .sim import analysis as A
from .sim.engine import Simulator

DEFAULT_SCENARIOS = [
    {"name": "adverse", "preset": "adverse"},
    {"name": "central", "preset": "central"},
    {"name": "aggressive", "preset": "aggressive"},
    {"name": "independent outcomes", "preset": "central", "independent_outcomes": True},
    {"name": "no AI speed-up", "preset": "central", "ai_multiplier": 1.0},
    {"name": "evidence has no effect", "preset": "central",
     "param_overrides": {"bonus_peer_reviewed": 0, "bonus_preprint": 0, "bonus_referral": 0, "bonus_artifact": 0,
                         "bonus_targeted_demo": 0}},
    {"name": "no relocation", "preset": "central", "allow_relocation": False},
    {"name": "quality dilution", "preset": "central", "breadth_penalty": 0.15},
]


def scenario_regret(con, strategy_ids, objective_id: str, n_worlds: int, scenarios=None) -> dict:
    """Expected score of every strategy under every scenario, and minimax regret.

    Scenarios mix parametric changes (hours, AI multiplier) with structural ones
    (independent outcomes, evidence effects switched off), so the table shows which
    rankings survive model uncertainty rather than only parameter uncertainty.
    """
    model = S.build_model(con)
    prof = S.objective(con, objective_id)
    defaults = get_meta(con, "objective_defaults", {})
    strats = S._strategy_objs(con, strategy_ids)
    eu: dict[str, dict[str, float]] = {}
    detail = {}
    for spec in scenarios or DEFAULT_SCENARIOS:
        sc = S.make_scenario(spec)
        sim = Simulator(model, sc, n_worlds=n_worlds, seed=4242, n_trace=0)
        res = {s.id: sim.run(s) for s in strats}
        ev = A.evaluate(res, prof, defaults)
        eu[spec["name"]] = {r["strategy"]: r["score"] for r in ev["ranking"]}
        detail[spec["name"]] = {
            "ranking": [{k: r[k] for k in ("strategy", "score", "feasible", "rank")} for r in ev["ranking"]],
            "position_by_grad": {sid: float(r["metrics"]["position_by_grad"].mean()) for sid, r in res.items()},
        }
    reg = A.regret_table(eu)
    return {"objective_id": objective_id, "n_worlds": n_worlds, "expected_scores": eu, "regret": reg,
            "detail": detail, "scenarios": [s["name"] for s in (scenarios or DEFAULT_SCENARIOS)]}


def tornado(con, strategy_ids, objective_id: str, n_worlds: int, params=None, scenario=None) -> dict:
    """Fix each parameter at its 10th and 90th percentile and record score changes and rank flips."""
    model = S.build_model(con)
    prof = S.objective(con, objective_id)
    defaults = get_meta(con, "objective_defaults", {})
    strats = S._strategy_objs(con, strategy_ids)
    base_sc = S.make_scenario(scenario)
    sim = Simulator(model, base_sc, n_worlds=n_worlds, seed=99, n_trace=0)
    base = A.evaluate({s.id: sim.run(s) for s in strats}, prof, defaults)
    base_scores = {r["strategy"]: r["score"] for r in base["ranking"]}
    best = base["ranking"][0]["strategy"]
    candidates = params or [k for k, p in model.params.items()
                            if p.dist.kind not in ("fixed",) and not k.startswith(("comp_", "prize_", "grant_", "ev_grant"))]
    rows = []
    for name in candidates:
        d = model.params[name].dist
        lo, hi = d.quantile(0.1), d.quantile(0.9)
        out = {"param": name, "origin": model.params[name].origin, "low_value": lo, "high_value": hi}
        for tag, val in (("low", lo), ("high", hi)):
            sc = S.make_scenario(scenario)
            sc.param_overrides = {**sc.param_overrides, name: val}
            s2 = Simulator(model, sc, n_worlds=n_worlds, seed=99, n_trace=0)
            ev = A.evaluate({s.id: s2.run(s) for s in strats}, prof, defaults)
            sc_scores = {r["strategy"]: r["score"] for r in ev["ranking"]}
            out[f"{tag}_score"] = sc_scores[best]
            out[f"{tag}_best"] = ev["ranking"][0]["strategy"]
        out["swing"] = abs(out["high_score"] - out["low_score"])
        out["flips_choice"] = out["low_best"] != best or out["high_best"] != best
        rows.append(out)
    rows.sort(key=lambda r: -r["swing"])
    return {"objective_id": objective_id, "strategy": best, "base_score": base_scores[best], "rows": rows,
            "n_worlds": n_worlds,
            "note": "One parameter at a time, others drawn from their distributions; interactions are not shown."}
