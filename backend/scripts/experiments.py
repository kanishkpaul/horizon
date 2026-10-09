"""Strategy experiments (brief Part 16). Reproducible: fixed seeds; results in research/experiments/.

Run: uv run --project backend python backend/scripts/experiments.py
"""
import json
import time
from pathlib import Path

from horizon import service as S
from horizon.analysis_jobs import scenario_regret, tornado
from horizon.db import ROOT, connect
from horizon.strategy_search import search_strategies

OUT = ROOT / "research" / "experiments"
OUT.mkdir(parents=True, exist_ok=True)
con = connect()
N = 4000
SEED = 20261009
res = {"generated": time.strftime("%Y-%m-%d %H:%M"), "n_worlds": N, "seed": SEED}


def brief(run):
    rows = []
    for r in run["analysis"]["ranking"]:
        m = run["strategy_results"][r["strategy"]]["metrics"]
        rows.append({"strategy": r["strategy"], "score": round(r["score"], 3), "se": round(r["se"], 3),
                     "feasible": r["feasible"], "position_by_grad": round(m["position_by_grad"]["mean"], 3),
                     "peer_reviewed": round(m["peer_reviewed"]["mean"], 3), "public_outputs": round(m["public_outputs"]["mean"], 2),
                     "optionality": round(m["optionality"]["mean"], 2), "autonomy": round(m["autonomy"]["mean"], 2),
                     "best_comp_p50": round(m["best_comp_lpa"]["p50"], 1), "founder_stage": round(m["founder_stage"]["mean"], 2),
                     "crunch_weeks": round(m["crunch_weeks"]["mean"], 2)})
    return {"run_id": run["id"], "ranking": rows, "top_vs_runner_up": run["analysis"]["top_vs_runner_up"],
            "pareto_front": run["analysis"]["pareto"]["front"],
            "voi_top": [{k: v[k] for k in ("param", "origin", "evppi", "decision_sensitive")} for v in run["analysis"].get("voi", [])[:8]]}


# A-G, P, Q, R: value-model experiments on the same worlds (central scenario)
base = S.run_simulation(con, objective_id="balanced", n_worlds=N, seed=SEED, label="EXP base (central)")
res["base_central_balanced"] = brief(base)
res["by_value_model"] = {}
for oid in ["balanced", "research_impact", "compensation", "entrepreneurial", "optionality", "autonomy", "robust", "upside_bounded"]:
    rr = S.reanalyze(con, base["id"], oid)
    res["by_value_model"][oid] = [{"strategy": r["strategy"], "score": round(r["score"], 3), "feasible": r["feasible"]} for r in rr["ranking"]]

# H, S: aggressive AI-assisted parallelization / optimistic productivity; T: optimistic assumptions wrong
for name, scn in {"aggressive": {"preset": "aggressive"}, "adverse": {"preset": "adverse"},
                  "paper_near_done": {"preset": "central", "effort_overrides": {"reg_paper_arr_oct": [6, 10, 16]}},
                  "paper_far": {"preset": "central", "effort_overrides": {"reg_paper_arr_oct": [40, 60, 90]}},
                  "no_evidence_effect": {"preset": "central", "param_overrides": {"bonus_peer_reviewed": 0, "bonus_preprint": 0, "bonus_referral": 0, "bonus_artifact": 0, "bonus_targeted_demo": 0}},
                  "low_replies": {"preset": "central", "param_overrides": {"p_reply_faculty": 0.12, "p_reply_founder": 0.1}},
                  "no_relocation": {"preset": "central", "allow_relocation": False}}.items():
    r = S.run_simulation(con, objective_id="balanced", scenario={**scn, "name": name}, n_worlds=N, seed=SEED, label=f"EXP {name}", voi=False)
    res[f"scenario_{name}"] = brief(r) | {"voi_top": None}

# F: robustness across models
res["regret_balanced"] = scenario_regret(con, None, "balanced", 2000)
res["regret_robust"] = scenario_regret(con, None, "robust", 2000)
# sensitivity
tor = tornado(con, None, "balanced", 1000)
res["tornado_balanced"] = {"strategy": tor["strategy"], "base": tor["base_score"],
                           "rows": [{k: r[k] for k in ("param", "origin", "low_score", "high_score", "swing", "flips_choice", "low_best", "high_best")} for r in tor["rows"][:15]]}
# strategy discovery
ss = search_strategies(con, "balanced", None, generations=10, population=28, n_worlds=600, seed=11)
res["search_balanced"] = {"front": [{k: f[k] for k in ("score", "se", "position_by_grad", "crunch_weeks", "peer_reviewed", "optionality", "feasible", "actions_not_in_any_preset")} | {"actions": f["spec"]["actions"], "max_parallel": f["spec"]["max_parallel"]} for f in ss["front"]],
                          "preset_scores": ss["preset_scores"], "evaluations": ss["evaluations"]}
(OUT / "experiments.json").write_text(json.dumps(res, indent=1, default=S._np))
print("wrote", OUT / "experiments.json")
