"""Strategy discovery by multi-objective evolutionary search (NSGA-II style).

A genome is a set of included actions plus a parallelism limit. Repair adds missing
prerequisites (e.g. collaboration projects need their outreach wave), and standard
contingency rules are attached automatically, so every candidate is an adaptive policy.
Candidates are scored on (objective score, P(position by graduation), -crunch weeks)
with common random numbers; the final front is re-evaluated with more worlds.
"""
from __future__ import annotations

import numpy as np

from . import service as S
from .db import get_meta
from .sim import analysis as A
from .sim.engine import Simulator, Strategy

KIND_RANK = {"admin": 0, "research": 1, "build": 2, "collaboration": 3, "outreach": 4, "application": 5,
             "competition": 6, "network": 7, "learning": 8, "information": 0}

NEEDS = {  # action -> actions it needs in the same policy
    "collab_research_1": ["outreach_faculty"], "collab_research_2": ["collab_research_1"],
    "collab_industry_1": ["outreach_founders"], "collab_industry_2": ["collab_industry_1"],
    "mcw_post_arxiv": ["mcw_writeup", "arxiv_endorsement"], "mcw_submit_ml_venue": ["mcw_writeup"],
    "mcw_submit_tmlr": ["mcw_writeup"], "reg_preprint": ["arxiv_endorsement"],
    "snorkel_benchmark_grant": ["mcw_benchmark_release"], "accelerator_application": ["startup_mvp"],
    "arr_service_contributor": ["reg_paper_arr_oct"], "reg_paper_arr_oct": ["arr_service_contributor"],
}
EXCLUSIVE = [("reg_paper_arr_oct", "reg_paper_arr_next"), ("mcw_submit_ml_venue", "mcw_submit_tmlr")]
NEVER_ALONE = {"reg_preprint": ["reg_paper_arr_oct", "reg_paper_arr_next"]}


def _pool(model) -> list[str]:
    skip = {"verify_sem8_policy"}
    return [a.id for a in model.actions if a.id not in skip and not a.id.startswith("opp_")] + \
           [a.id for a in model.actions if a.id.startswith("opp_")]


def _repair(genes: set[str], rng) -> set[str]:
    g = set(genes)
    for a, b in EXCLUSIVE:
        if a in g and b in g:
            g.discard(b if rng.random() < 0.5 else a)
    changed = True
    while changed:
        changed = False
        for a, needs in NEEDS.items():
            if a in g:
                for n in needs:
                    if n not in g and not any((n, x) in EXCLUSIVE or (x, n) in EXCLUSIVE for x in g):
                        g.add(n)
                        changed = True
    for a, any_of in NEVER_ALONE.items():
        if a in g and not any(x in g for x in any_of):
            g.discard(a)
    return g


def to_strategy(genes: set[str], max_parallel: int, model, sid: str) -> Strategy:
    acts = [model.action(a) for a in genes]
    acts.sort(key=lambda a: (a.deadline_week if a.deadline_week is not None else 1e9, KIND_RANK.get(a.kind, 9)))
    order = [a.id for a in acts]
    rules, contingent = [], []
    if "reg_paper_arr_oct" in genes:
        contingent.append("reg_paper_arr_next")
        rules.append({"label": "Missed October ARR → January cycle", "when": {"missed": "reg_paper_arr_oct"},
                      "enable": ["reg_paper_arr_next"]})
    if "mcw_submit_ml_venue" in genes:
        contingent.append("mcw_submit_tmlr")
        rules.append({"label": "Missed ML venue → TMLR", "when": {"missed": "mcw_submit_ml_venue"},
                      "enable": ["mcw_submit_tmlr"]})
    if "outreach_faculty" in genes and "collab_research_2" not in genes:
        contingent.append("collab_research_2")
        rules.append({"label": "Two research replies → second collaboration", "when":
                      {"token": "leads_research", "op": ">=", "value": 2}, "enable": ["collab_research_2"]})
    return Strategy(id=sid, name=sid, actions=order, rules=rules, contingent=contingent, max_parallel=max_parallel)


def _nondominated_sort(F: np.ndarray) -> list[list[int]]:
    n = len(F)
    dom = [[] for _ in range(n)]
    cnt = np.zeros(n, dtype=int)
    for i in range(n):
        for j in range(n):
            if i != j and np.all(F[i] >= F[j]) and np.any(F[i] > F[j]):
                dom[i].append(j)
            elif i != j and np.all(F[j] >= F[i]) and np.any(F[j] > F[i]):
                cnt[i] += 1
    fronts = [[i for i in range(n) if cnt[i] == 0]]
    while fronts[-1]:
        nxt = []
        for i in fronts[-1]:
            for j in dom[i]:
                cnt[j] -= 1
                if cnt[j] == 0:
                    nxt.append(j)
        fronts.append(nxt)
    return [f for f in fronts if f]


def _crowding(F: np.ndarray, idx: list[int]) -> dict[int, float]:
    d = {i: 0.0 for i in idx}
    if len(idx) <= 2:
        return {i: float("inf") for i in idx}
    for k in range(F.shape[1]):
        srt = sorted(idx, key=lambda i: F[i, k])
        d[srt[0]] = d[srt[-1]] = float("inf")
        span = F[srt[-1], k] - F[srt[0], k] or 1.0
        for a, b, c in zip(srt, srt[1:], srt[2:]):
            d[b] += (F[c, k] - F[a, k]) / span
    return d


def search_strategies(con, objective_id="balanced", scenario=None, generations=8, population=24, n_worlds=500,
                      seed=7) -> dict:
    model = S.build_model(con)
    prof = S.objective(con, objective_id)
    defaults = get_meta(con, "objective_defaults", {})
    sc = S.make_scenario(scenario)
    sim = Simulator(model, sc, n_worlds=n_worlds, seed=seed, n_trace=0)
    pool = _pool(model)
    rng = np.random.default_rng(seed)
    cache: dict[tuple, dict] = {}

    def evaluate(genes: frozenset, mp: int) -> dict:
        key = (genes, mp)
        if key in cache:
            return cache[key]
        st = to_strategy(set(genes), mp, model, "cand")
        r = sim.run(st)
        u = A.utility(r["metrics"], prof, defaults)
        cons = A.check_constraints(r["metrics"], prof.get("constraints", []))
        feasible = all(c["satisfied"] for c in cons if c.get("hard"))
        f = np.array([A.risk_value(u, prof.get("risk")) - (0 if feasible else 10.0),
                      float(r["metrics"]["position_by_grad"].mean()),
                      -float(r["metrics"]["crunch_weeks"].mean())])
        cache[key] = {"f": f, "feasible": feasible}
        return cache[key]

    # seed population with presets plus random portfolios
    presets = [s for s in S.strategies(con)]
    popn: list[tuple[frozenset, int]] = []
    for p in presets:
        genes = {a for a in p["actions"] if a in pool}
        popn.append((frozenset(_repair(genes, rng)), int(p.get("max_parallel", 4))))
    while len(popn) < population:
        k = rng.integers(5, 18)
        genes = set(rng.choice(pool, size=min(k, len(pool)), replace=False).tolist())
        popn.append((frozenset(_repair(genes, rng)), int(rng.integers(3, 7))))
    history = []
    for gen in range(generations):
        # variation: uniform crossover + bit-flip mutation + parallelism tweak
        children = []
        while len(children) < population:
            a, b = rng.choice(len(popn), 2, replace=False)
            ga, gb = set(popn[a][0]), set(popn[b][0])
            child = {x for x in ga | gb if (x in ga and x in gb) or rng.random() < 0.5}
            for x in pool:
                if rng.random() < 1.5 / len(pool):
                    child ^= {x}
            mp = popn[a][1] if rng.random() < 0.5 else popn[b][1]
            if rng.random() < 0.2:
                mp = int(np.clip(mp + rng.choice([-1, 1]), 2, 8))
            children.append((frozenset(_repair(child, rng)), mp))
        union = list(dict.fromkeys(popn + children))
        F = np.stack([evaluate(g, mp)["f"] for g, mp in union])
        fronts = _nondominated_sort(F)
        nxt = []
        for fr in fronts:
            if len(nxt) + len(fr) <= population:
                nxt += fr
            else:
                cd = _crowding(F, fr)
                nxt += sorted(fr, key=lambda i: -cd[i])[: population - len(nxt)]
                break
        popn = [union[i] for i in nxt]
        history.append({"generation": gen + 1, "evaluations": len(cache),
                        "best_score": float(F[:, 0].max()), "front_size": len(fronts[0])})
    # final front, re-evaluated with more worlds
    F = np.stack([evaluate(g, mp)["f"] for g, mp in popn])
    front = [popn[i] for i in _nondominated_sort(F)[0]]
    big = Simulator(model, sc, n_worlds=max(2000, n_worlds * 4), seed=seed + 1, n_trace=0)
    out = []
    for k, (genes, mp) in enumerate(front[:12]):
        st = to_strategy(set(genes), mp, model, f"search_{k + 1}")
        r = big.run(st)
        u = A.utility(r["metrics"], prof, defaults)
        cons = A.check_constraints(r["metrics"], prof.get("constraints", []))
        new_vs_presets = sorted(set(genes) - set().union(*[set(p["actions"]) for p in presets]))
        out.append({
            "spec": st.to_dict() | {"name": f"Discovered #{k + 1}", "description":
                                    f"Found by NSGA-II search under '{prof.get('name')}'. {len(genes)} actions, "
                                    f"max {mp} in parallel."},
            "score": A.risk_value(u, prof.get("risk")), "se": float(u.std(ddof=1) / np.sqrt(len(u))),
            "position_by_grad": float(r["metrics"]["position_by_grad"].mean()),
            "crunch_weeks": float(r["metrics"]["crunch_weeks"].mean()),
            "peer_reviewed": float(r["metrics"]["peer_reviewed"].mean()),
            "optionality": float(r["metrics"]["optionality"].mean()),
            "feasible": all(c["satisfied"] for c in cons if c.get("hard")),
            "actions_not_in_any_preset": new_vs_presets,
        })
    out.sort(key=lambda r: -r["score"])
    preset_scores = {}
    for p in presets:
        st = Strategy.from_dict(p)
        r = big.run(st)
        preset_scores[p["id"]] = A.risk_value(A.utility(r["metrics"], prof, defaults), prof.get("risk"))
    return {"objective_id": objective_id, "front": out, "history": history, "evaluations": len(cache),
            "preset_scores": preset_scores,
            "method": "NSGA-II (non-dominated sorting + crowding distance) over action subsets and parallelism; "
                      "objectives: profile score, P(position by graduation), −crunch weeks; CRN within a generation."}
