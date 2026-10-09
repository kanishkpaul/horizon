"""Theater specs: one simulated world of one strategy, turned into a scene list.

The same spec drives the interactive Strategy Theater and the rendered video, so the
two always describe the same model state. A spec records the run, model fingerprint,
seed and world index it came from.
"""
from __future__ import annotations

from . import service as S

KIND_ORDER = {"admin": 0, "research": 1, "build": 2, "collaboration": 3, "outreach": 4, "application": 5,
              "competition": 6, "network": 7, "learning": 8, "information": 9}


def worlds_summary(run: dict, strategy: str) -> list[dict]:
    """Per traced world: offers and outcomes, so the user can pick a typical or extreme realization."""
    res = run["strategy_results"][strategy]
    out: dict[int, dict] = {}
    for e in res["trace"]:
        w = out.setdefault(e["world"], {"world": e["world"], "offers": [], "outcomes": 0, "missed": 0})
        if e["type"] == "offer":
            w["offers"].append(e["label"])
        elif e["type"] == "outcome":
            w["outcomes"] += 1
        elif e["type"] == "missed":
            w["missed"] += 1
    return sorted(out.values(), key=lambda w: w["world"])


def build_spec(con, run_id: str, strategy: str, world: int) -> dict:
    run = S.get_run(con, run_id)
    if not run:
        raise KeyError(run_id)
    if strategy not in run["strategy_results"]:
        raise KeyError(strategy)
    res = run["strategy_results"][strategy]
    events = [e for e in res["trace"] if e["world"] == world]
    spec_s = next(s for s in run["strategies"] if s["id"] == strategy)
    acts = run["actions"]
    used = []
    for e in events:
        if e["action"] and e["action"] not in used:
            used.append(e["action"])
    lanes = sorted(used, key=lambda a: (min((e["week"] for e in events if e["action"] == a), default=99)))
    # scenes for captions: the moments a reader needs to understand the trajectory
    scenes = [{"t": 0.0, "kind": "intro",
               "text": f"One simulated world (#{world}) under '{spec_s['name']}'. Every bar is an action the policy "
                       "chose; outcomes are drawn from the model's probabilities, not predicted."}]
    for e in events:
        if e["type"] in ("offer", "rule", "missed", "exogenous") or (e["type"] == "outcome" and e["label"] not in
                                                                       ("No reply", "Otherwise")):
            name = acts.get(e["action"], {}).get("name", e["action"]) if e["action"] else ""
            txt = {
                "offer": f"Offer received: {e['label'].replace('_', ' ')} (via {name}).",
                "rule": f"Policy rule fires: {e['label']}.",
                "missed": f"Deadline missed: {name}.",
                "exogenous": f"Outside event: {e['label']}.",
                "outcome": f"{name}: {e['label']}.",
            }[e["type"]]
            scenes.append({"t": e["week"], "kind": e["type"], "text": txt, "action": e["action"]})
    an = run["analysis"]
    rank = next((r for r in an["ranking"] if r["strategy"] == strategy), None)
    m = res["metrics"]
    scenes.append({"t": float(run["horizon_weeks"]), "kind": "outro",
                   "text": f"Across all {run['n_worlds']:,} worlds this strategy secured a position by graduation "
                           f"{m['position_by_grad']['mean']:.0%} of the time and averaged "
                           f"{m['peer_reviewed']['mean']:.2f} peer-reviewed papers. This world is one sample, not "
                           "the expected future."})
    scenes.sort(key=lambda s: s["t"])
    return {
        "run_id": run_id, "model_version": run["model_version"] if "model_version" in run else None,
        "model_fingerprint": run.get("model_fingerprint"), "dataset_version": run.get("dataset_version"),
        "seed": run["seed"], "n_worlds": run["n_worlds"], "scenario": run["scenario"], "objective": run["objective"]["name"],
        "strategy": strategy, "strategy_name": spec_s["name"], "world": world, "start_date": run["start_date"],
        "horizon_weeks": run["horizon_weeks"], "graduation_week": run["graduation_week"],
        "lanes": [{"id": a, "name": acts.get(a, {}).get("name", a), "deadline_week": acts.get(a, {}).get("deadline_week")}
                  for a in lanes],
        "events": events, "scenes": scenes,
        "series": {"position": res["series"]["position"], "peer_reviewed": res["series"]["peer_reviewed"]},
        "summary": {k: m[k]["mean"] for k in ("position_by_grad", "peer_reviewed", "public_outputs", "optionality",
                                             "crunch_weeks")},
        "rank": rank["rank"] if rank else None,
    }
