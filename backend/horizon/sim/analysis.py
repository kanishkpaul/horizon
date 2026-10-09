"""Decision analysis over simulation output.

All functions take world-level arrays produced with common random numbers, so
differences between strategies are paired comparisons on identical worlds.
"""
from __future__ import annotations

import math

import numpy as np

DIRECTION = {  # +1 more is better, -1 less is better
    "peer_reviewed": 1, "workshop": 1, "public_outputs": 1, "best_comp_lpa": 1, "position_by_grad": 1,
    "position_by_horizon": 1, "optionality": 1, "autonomy": 1, "founder_stage": 1, "ties": 1, "adoption": 1,
    "cash_lpa": 1, "crunch_weeks": -1, "hours_used": -1,
}

STATS = ("mean", "p10", "p50", "p90")


def summarize(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    n = len(x)
    return {
        "mean": float(x.mean()), "sd": float(x.std(ddof=1)) if n > 1 else 0.0,
        "se": float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0,
        "p10": float(np.quantile(x, 0.1)), "p50": float(np.quantile(x, 0.5)), "p90": float(np.quantile(x, 0.9)),
        "p_pos": float((x > 0).mean()),
    }


def histogram(x: np.ndarray, bins: int = 24) -> dict:
    x = np.asarray(x, dtype=float)
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return {"edges": [lo, lo + 1], "counts": [int(len(x))]}
    uniq = np.unique(x)
    if len(uniq) <= bins:  # discrete metric: one bar per value
        counts = [int((x == u).sum()) for u in uniq]
        return {"values": [float(u) for u in uniq], "counts": counts}
    c, e = np.histogram(x, bins=bins)
    return {"edges": [float(v) for v in e], "counts": [int(v) for v in c]}


# ---------------------------------------------------------------- objectives
def utility(metrics: dict[str, np.ndarray], profile: dict, defaults: dict) -> np.ndarray:
    refs = {**defaults.get("refs", {}), **profile.get("refs", {})}
    caps = {**defaults.get("caps", {}), **profile.get("caps", {})}
    n = len(next(iter(metrics.values())))
    u = np.zeros(n)
    for k, w in profile.get("weights", {}).items():
        if k not in metrics or w == 0:
            continue
        g = metrics[k] / float(refs.get(k, 1.0))
        if w > 0:  # costs are never capped (adversarial review #5); benefits saturate at an explicit cap
            g = np.minimum(g, float(caps.get(k, 3.0)))
        u = u + float(w) * g
    return u


def risk_value(u: np.ndarray, risk: dict) -> float:
    m = (risk or {}).get("measure", "mean")
    if m == "mean":
        return float(u.mean())
    if m == "cvar":
        a = float(risk.get("alpha", 0.2))
        k = max(1, int(math.ceil(a * len(u))))
        return float(np.sort(u)[:k].mean())
    if m == "quantile":
        return float(np.quantile(u, float(risk.get("alpha", 0.5))))
    raise ValueError(m)


def stat_of(x: np.ndarray, stat: str) -> float:
    if stat == "mean":
        return float(np.mean(x))
    if stat.startswith("p"):
        return float(np.quantile(x, int(stat[1:]) / 100))
    raise ValueError(stat)


def check_constraints(metrics: dict[str, np.ndarray], constraints: list[dict]) -> list[dict]:
    out = []
    for c in constraints or []:
        v = stat_of(metrics[c["metric"]], c.get("stat", "mean"))
        ok = {">=": v >= c["value"], "<=": v <= c["value"], ">": v > c["value"], "<": v < c["value"]}[c["op"]]
        out.append({**c, "observed": v, "satisfied": bool(ok)})
    return out


def evaluate(results: dict[str, dict], profile: dict, defaults: dict) -> dict:
    """Rank strategies under one objective profile."""
    rows = []
    U = {}
    for sid, r in results.items():
        u = utility(r["metrics"], profile, defaults)
        U[sid] = u
        cons = check_constraints(r["metrics"], profile.get("constraints", []))
        feasible = all(c["satisfied"] for c in cons if c.get("hard"))
        rows.append({"strategy": sid, "score": risk_value(u, profile.get("risk")), "mean_utility": float(u.mean()),
                     "se": float(u.std(ddof=1) / math.sqrt(len(u))), "p10": float(np.quantile(u, 0.1)),
                     "p90": float(np.quantile(u, 0.9)), "feasible": feasible, "constraints": cons})
    rows.sort(key=lambda r: (not r["feasible"], -r["score"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    # paired comparison of the top two (common random numbers)
    resolved = None
    if len(rows) >= 2:
        a, b = rows[0]["strategy"], rows[1]["strategy"]
        d = U[a] - U[b]
        se = float(d.std(ddof=1) / math.sqrt(len(d)))
        z = float(d.mean() / se) if se > 0 else float("inf")
        resolved = {"top": a, "runner_up": b, "mean_diff": float(d.mean()), "se": se, "z": z,
                    "p_world_top_better": float((d > 0).mean()), "resolved": bool(abs(z) > 2.5)}
    return {"ranking": rows, "utilities": U, "top_vs_runner_up": resolved}


def dominance_matrix(U: dict[str, np.ndarray]) -> dict:
    """P(strategy i yields higher utility than j in the same world)."""
    ids = list(U)
    M = [[float((U[a] > U[b]).mean()) if a != b else None for b in ids] for a in ids]
    return {"ids": ids, "p_better": M}


def pareto_front(points: dict[str, dict[str, float]], metrics: list[str]) -> list[str]:
    """Strategies not dominated on the mean of the selected metrics."""
    ids = list(points)
    front = []
    for a in ids:
        dominated = False
        for b in ids:
            if a == b:
                continue
            ge = all(DIRECTION.get(m, 1) * (points[b][m] - points[a][m]) >= -1e-12 for m in metrics)
            gt = any(DIRECTION.get(m, 1) * (points[b][m] - points[a][m]) > 1e-9 for m in metrics)
            if ge and gt:
                dominated = True
                break
        if not dominated:
            front.append(a)
    return front


def regret_table(eu: dict[str, dict[str, float]]) -> dict:
    """eu[scenario][strategy] -> expected score. Minimax regret across scenarios."""
    scen = list(eu)
    strats = list(next(iter(eu.values())))
    best = {s: max(eu[s].values()) for s in scen}
    reg = {k: {s: best[s] - eu[s][k] for s in scen} for k in strats}
    worst = {k: max(reg[k].values()) for k in strats}
    order = sorted(strats, key=lambda k: worst[k])
    return {"scenarios": scen, "regret": reg, "max_regret": worst, "minimax_choice": order[0], "order": order}


# ---------------------------------------------------------------- value of information
def evppi(U: dict[str, np.ndarray], theta: np.ndarray, bins: int = 10, n_perm: int = 20, seed: int = 0) -> dict:
    """Expected value of partial perfect information about one parameter.

    Nonparametric estimate: condition on quantile bins of the parameter (each world's
    draw is shared across strategies), choose the best strategy within each bin, and
    compare with choosing once. Estimates are biased upward by bin noise, so the same
    statistic on permuted parameter values is reported as a noise floor.
    """
    ids = list(U)
    Umat = np.stack([U[k] for k in ids])  # S x N
    base = float(Umat.mean(axis=1).max())

    def stat(th):
        uniq = np.unique(th)
        if len(uniq) <= bins:
            groups = [th == v for v in uniq]
        else:
            qs = np.quantile(th, np.linspace(0, 1, bins + 1))
            idx = np.clip(np.searchsorted(qs, th, side="right") - 1, 0, bins - 1)
            groups = [idx == b for b in range(bins)]
        tot = 0.0
        n = len(th)
        choices = []
        for g in groups:
            if g.sum() == 0:
                continue
            means = Umat[:, g].mean(axis=1)
            j = int(means.argmax())
            choices.append(ids[j])
            tot += means[j] * g.sum() / n
        return tot - base, choices

    val, choices = stat(theta)
    rng = np.random.default_rng(seed)
    floor = [stat(rng.permutation(theta))[0] for _ in range(n_perm)]
    fl = float(np.mean(floor))
    return {"evppi_raw": float(val), "noise_floor": fl, "evppi": float(max(val - fl, 0.0)),
            "floor_p95": float(np.quantile(floor, 0.95)), "best_by_bin": choices,
            "decision_sensitive": len(set(choices)) > 1 and val > float(np.quantile(floor, 0.95))}


def global_sensitivity(u: np.ndarray, params: dict[str, np.ndarray]) -> list[dict]:
    """Spearman rank correlation between each parameter draw and world utility."""
    from scipy.stats import spearmanr
    out = []
    for k, th in params.items():
        if np.allclose(th, th[0]):
            continue
        rho = spearmanr(th, u).statistic
        if not np.isnan(rho):
            out.append({"param": k, "rho": float(rho)})
    out.sort(key=lambda r: -abs(r["rho"]))
    return out


def convergence(u: np.ndarray, n_batches: int = 20) -> dict:
    """Batch-means standard error and the running mean, to show whether n is large enough."""
    n = len(u)
    b = n // n_batches
    means = [float(u[i * b:(i + 1) * b].mean()) for i in range(n_batches)] if b > 0 else []
    se_batch = float(np.std(means, ddof=1) / math.sqrt(len(means))) if len(means) > 1 else None
    steps = np.unique(np.linspace(max(10, n // 50), n, 30).astype(int))
    running = [{"n": int(k), "mean": float(u[:k].mean())} for k in steps]
    se = float(u.std(ddof=1) / math.sqrt(n))
    return {"n": n, "se_iid": se, "se_batch_means": se_batch, "running_mean": running,
            "relative_se": float(se / abs(u.mean())) if abs(u.mean()) > 1e-9 else None}
