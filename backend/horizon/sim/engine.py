"""Vectorized discrete-time simulation of an adaptive strategy.

All N simulated worlds advance together, one week at a time. Each world draws its
own parameter values (epistemic uncertainty) and latent factors (shared shocks that
correlate outcomes), then outcomes are drawn given those values (aleatory noise).

Per week:
  1. resolve external responses that fall due (tokens, offers, metrics change)
  2. fire policy rules (enable/disable actions) on the new state
  3. compute effective hours (academic load, disruptions, diminishing returns,
     context switching)
  4. allocate hours to eligible actions in priority order (deadline-urgent first)
  5. complete actions, schedule their external stages, mark missed deadlines

The model is a stochastic state-transition system over an AND/OR action graph
(prerequisites are conditions on state; outcomes add state). See MODEL_CARD.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .conditions import compile_cond
from .model import MAX_METRICS, SUM_METRICS, Action, Model, Outcome, ProbSpec
from .params import ParamSet, stream

TODO, ACTIVE, DONE, MISSED, DROPPED, OFF = 0, 1, 2, 3, 4, 5
STATUS_NAMES = {TODO: "todo", ACTIVE: "active", DONE: "done", MISSED: "missed", DROPPED: "dropped", OFF: "off"}

REPORT_METRICS = ("peer_reviewed", "workshop", "public_outputs", "best_comp_lpa", "position_by_grad",
                  "position_by_horizon", "optionality", "autonomy", "founder_stage", "ties", "adoption",
                  "cash_lpa", "crunch_weeks", "hours_used")


@dataclass
class Scenario:
    name: str = "central"
    weekly_hours: float = 60.0          # total weekly work budget, academics included
    ai_multiplier: float = 1.5          # speed-up on the automatable share (<1 = slowdown)
    effort_bias: float = 1.15           # mean multiplier on estimated effort (planning fallacy)
    sustainable_cap: float = 49.0       # hours/week above which marginal output falls (Pencavel 2014)
    switch_cost: float = 0.04           # fraction of hours lost per concurrent action beyond focus_k
    focus_k: int = 3
    academic: list = field(default_factory=lambda: [
        # [start_week, end_week, hours]  (placeholder calendar; see ASSUMPTIONS.md)
        [0, 7.3, 20], [7.3, 10.3, 35], [10.3, 12.4, 0], [12.4, 33.3, 14], [33.3, 37.0, 25],
    ])
    factor_corr: float = 0.2
    independent_outcomes: bool = False
    allow_relocation: bool = True
    param_overrides: dict = field(default_factory=dict)
    disruption_hours_factor: float = 0.4

    @classmethod
    def preset(cls, name: str) -> "Scenario":
        # Evidence (research/agents/params): planning fallacy ~1.64x own estimates (Buehler 1994);
        # AI speed-ups from -19% (METR 2025, experienced devs) to +56% (Copilot greenfield).
        p = {
            "adverse": dict(weekly_hours=50, ai_multiplier=0.85, effort_bias=1.75),
            "central": dict(weekly_hours=60, ai_multiplier=1.25, effort_bias=1.4),
            "aggressive": dict(weekly_hours=72, ai_multiplier=2.0, effort_bias=1.1),
        }[name]
        return cls(name=name, **p)

    def academic_hours(self, week: int) -> float:
        for lo, hi, h in self.academic:
            if lo <= week < hi:
                return float(h)
        return 0.0


@dataclass
class Strategy:
    id: str
    name: str
    actions: list[str]                     # priority order
    rules: list[dict] = field(default_factory=list)
    contingent: list[str] = field(default_factory=list)   # off until a rule enables them
    max_parallel: int = 4
    hours_scale: float = 1.0
    description: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Strategy":
        return cls(id=d["id"], name=d.get("name", d["id"]), actions=list(d.get("actions", [])),
                   rules=list(d.get("rules", [])), contingent=list(d.get("contingent", [])),
                   max_parallel=int(d.get("max_parallel", 4)), hours_scale=float(d.get("hours_scale", 1.0)),
                   description=d.get("description", ""))

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "actions": self.actions, "rules": self.rules,
                "contingent": self.contingent, "max_parallel": self.max_parallel,
                "hours_scale": self.hours_scale, "description": self.description}


class State:
    """Struct-of-arrays world state for all simulated worlds."""

    def __init__(self, n: int, actions: list[Action]):
        self.n = n
        self.ones = np.ones(n, dtype=bool)
        self.week = 0.0
        self.tokens: dict[str, np.ndarray] = {}
        self.idx = {a.id: i for i, a in enumerate(actions)}
        A = len(actions)
        self.status = np.full((A, n), OFF, dtype=np.int8)
        self.remaining = np.zeros((A, n))
        self.started = np.full((A, n), np.nan)
        self.completed = np.full((A, n), np.nan)
        self.stage = np.full((A, n), -1, dtype=np.int16)     # index of pending stage, -1 none
        self.stage_due = np.full((A, n), np.inf)
        self.stage_p: dict[tuple[int, int], list[np.ndarray]] = {}
        self.outcome_hits: dict[tuple[int, int, int], np.ndarray] = {}

    def token(self, name: str) -> np.ndarray:
        t = self.tokens.get(name)
        if t is None:
            t = self.tokens[name] = np.zeros(self.n)
        return t

    def status_of(self, aid: str) -> np.ndarray:
        if aid not in self.idx:
            return np.full(self.n, OFF, dtype=np.int8)
        return self.status[self.idx[aid]]


def effective_hours(total: float, cap: float = 49.0) -> float:
    """Output-equivalent hours. Linear to `cap`, 0.4 marginal for the next 14 h, flat beyond.

    Shape follows Pencavel (2014): output proportional to hours up to ~49 h/week and
    no further gain beyond ~63 h. The data are from munitions workers, so this is a
    scenario assumption for knowledge work, not a measured law.
    """
    return min(total, cap) + 0.4 * min(max(total - cap, 0.0), 14.0)


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class Simulator:
    def __init__(self, model: Model, scenario: Scenario, n_worlds: int = 2000, seed: int = 7,
                 n_trace: int = 24, horizon_weeks: int | None = None):
        self.m = model
        self.sc = scenario
        self.n = n_worlds
        self.seed = seed
        self.n_trace = min(n_trace, n_worlds)
        self.T = horizon_weeks or model.horizon_weeks
        overrides = dict(scenario.param_overrides)
        self.P = ParamSet(model.params, seed, n_worlds, overrides)
        self.z = self._factors()

    # ---- shared randomness (identical across strategies with the same seed) ----
    def _factors(self) -> dict[str, np.ndarray]:
        rng = stream(self.seed, "factors")
        k = len(self.m.factors)
        C = np.full((k, k), self.sc.factor_corr)
        np.fill_diagonal(C, 1.0)
        Z = rng.multivariate_normal(np.zeros(k), C, self.n)
        return {f: Z[:, i] for i, f in enumerate(self.m.factors)}

    def _u(self, *key) -> np.ndarray:
        return stream(self.seed, "u", *[str(k) for k in key]).random(self.n)

    def _effort(self, a: Action) -> np.ndarray:
        lo, mo, hi = a.effort
        base = stream(self.seed, "effort", a.id).triangular(lo, mo, hi, self.n) if hi > lo else np.full(self.n, lo)
        gsd = float(self.P["effort_noise_gsd"][0]) if "effort_noise_gsd" in self.m.params else 1.0
        noise = np.exp(stream(self.seed, "effort_noise", a.id).normal(0.0, math.log(gsd), self.n) - 0.5 * math.log(gsd) ** 2)
        raw = base * noise * self.sc.effort_bias
        auto = a.automatable
        return raw * ((1 - auto) + auto / max(self.sc.ai_multiplier, 1e-3))

    def _delay(self, spec) -> np.ndarray:
        if isinstance(spec, (int, float)):
            return np.full(self.n, float(spec))
        return np.maximum(self.P.value_or_param(spec), 0.0)

    def _p(self, ps: ProbSpec, S: State) -> np.ndarray:
        base = self.P.value_or_param(ps.base)
        x = logit(base)
        for sh in ps.shifts:
            v = self.P[sh["param"]]
            if "token" in sh:
                x = x + v * np.minimum(S.token(sh["token"]), float(sh.get("cap", 1)))
            else:
                x = x + v
        if not self.sc.independent_outcomes:
            for f, load in ps.factors.items():
                x = x + self.P.value_or_param(load) * self.z[f]
        return sigmoid(x)

    # ---- main loop ----
    def run(self, strat: Strategy) -> dict:
        m, n, T = self.m, self.n, self.T
        acts = m.actions
        S = State(n, acts)
        cond_state = _CondView(S)

        for name, v in m.initial_tokens.items():
            if isinstance(v, dict):
                d = self.P[v["param"]]
                S.tokens[name] = (1.0 - d) if v.get("invert") else d.copy()
            else:
                S.tokens[name] = np.full(n, float(v))

        order = [a for a in strat.actions if a in S.idx]
        unknown = [a for a in strat.actions + strat.contingent if a not in S.idx]
        prio = {aid: i for i, aid in enumerate(order + [c for c in strat.contingent if c in S.idx])}
        for aid in order:
            a = acts[S.idx[aid]]
            if a.requires_relocation and not self.sc.allow_relocation:
                continue
            S.status[S.idx[aid]] = TODO
        for i, a in enumerate(acts):
            S.remaining[i] = self._effort(a)

        rules = [(compile_cond(r["when"]), r) for r in strat.rules]
        fired = [np.zeros(n, dtype=bool) for _ in rules]

        metrics = {k: np.zeros(n) for k in SUM_METRICS + MAX_METRICS}
        offers = {c: np.zeros(n, dtype=bool) for c in m.offer_classes}
        offer_week = {c: np.full(n, np.inf) for c in m.offer_classes}
        comp = {c: (self.P[v["comp"]] if v.get("comp") else np.zeros(n)) for c, v in m.offer_classes.items()}
        crunch = np.zeros(n)
        hours_used = np.zeros(n)
        prev_active = np.zeros(n)
        disrupt_p = self.P["p_disruption_week"] if "p_disruption_week" in m.params else np.zeros(n)
        exo_u = {e["id"]: stream(self.seed, "exo", e["id"]).random((T, n)) for e in m.exogenous}
        u_disrupt = stream(self.seed, "disruption").random((T, n))

        trace: list[dict] = []
        tw = self.n_trace
        series = {k: [] for k in ("hours", "position", "peer_reviewed", "public_outputs", "crunch", "offers_any",
                                  "ties")}
        unlock_series: dict[str, list[float]] = {}

        def log(mask, week, kind, a: Action | None, label, extra=None):
            if tw == 0:
                return
            hit = np.nonzero(mask[:tw])[0]
            for w in hit:
                trace.append({"world": int(w), "week": round(float(week), 3), "type": kind,
                              "action": a.id if a else None, "label": label, **(extra or {})})

        def apply_outcome(ai: int, o: Outcome, mask: np.ndarray, mult: np.ndarray, week: float):
            for tk, dv in o.tokens.items():
                S.token(tk)[mask] += float(dv) * mult[mask]
            for mk, mv in o.metrics.items():
                if mk == "offer":
                    newly = mask & ~offers[mv]
                    offers[mv] |= mask
                    offer_week[mv] = np.where(newly, week, offer_week[mv])
                    continue
                val = self.P.value_or_param(mv)
                if mk in MAX_METRICS:
                    metrics[mk] = np.where(mask, np.maximum(metrics[mk], val), metrics[mk])
                else:
                    metrics[mk] = metrics[mk] + np.where(mask, val * mult, 0.0)

        def schedule_stage(ai: int, si: int, mask: np.ndarray, now: float):
            a = acts[ai]
            if si >= len(a.stages):
                S.stage[ai][mask] = -1
                return
            st = a.stages[si]
            due = now + self._delay(st.delay)
            S.stage[ai] = np.where(mask, si, S.stage[ai])
            S.stage_due[ai] = np.where(mask, due, S.stage_due[ai])
            # freeze outcome probabilities at the moment the stage starts (evidence at submission time)
            ps = [self._p(o.p, S) if (o.p and o.p.at == "start") else np.zeros(n) for o in st.outcomes]
            key = (ai, si)
            old = S.stage_p.get(key)
            S.stage_p[key] = ps if old is None else [np.where(mask, p, q) for p, q in zip(ps, old)]

        def resolve(ai: int, now_week: int):
            a = acts[ai]
            due = (S.stage[ai] >= 0) & (S.stage_due[ai] < now_week + 1)
            if not due.any():
                return
            si_arr = S.stage[ai]
            for si in np.unique(si_arr[due]):
                mask = due & (si_arr == si)
                st = a.stages[si]
                ps = S.stage_p[(ai, si)]
                u = self._u("stage", a.id, si)
                remaining = mask.copy()
                cum = np.zeros(n)
                any_hit = np.zeros(n, dtype=bool)
                continue_mask = np.zeros(n, dtype=bool)
                for oi, (o, p) in enumerate(zip(st.outcomes, ps)):
                    if o.p is not None and o.p.at == "resolve":
                        p = self._p(o.p, S)
                    if o.count:
                        k = stats.binom.ppf(u, o.count, np.clip(p, 0, 1))
                        k = np.where(np.isnan(k), 0, k)
                        hit = remaining & (k > 0)
                        mult = k
                    else:
                        lo = cum
                        cum = cum + (1 - cum) * p
                        hit = remaining & (u >= lo) & (u < cum)
                        mult = np.ones(n)
                    if hit.any():
                        apply_outcome(ai, o, hit, mult, now_week + 0.5)
                        S.outcome_hits[(ai, si, oi)] = S.outcome_hits.get((ai, si, oi), np.zeros(n, bool)) | hit
                        log(hit, now_week + 0.5, "outcome", a, o.label, {"stage": st.name})
                        if any(k == "offer" for k in o.metrics):
                            log(hit, now_week + 0.5, "offer", a, o.metrics["offer"])
                    any_hit |= hit
                    continue_mask |= hit
                    remaining &= ~hit
                miss = mask & ~any_hit
                if miss.any():
                    apply_outcome(ai, st.otherwise, miss, np.ones(n), now_week + 0.5)
                    S.outcome_hits[(ai, si, -1)] = S.outcome_hits.get((ai, si, -1), np.zeros(n, bool)) | miss
                    log(miss, now_week + 0.5, "outcome", a, st.otherwise.label, {"stage": st.name})
                S.stage[ai][mask] = -1
                S.stage_due[ai][mask] = np.inf
                if si + 1 < len(a.stages) and continue_mask.any():
                    schedule_stage(ai, si + 1, continue_mask, now_week + 1)

        for t in range(T):
            S.week = float(t)
            # 1. external responses
            for ai in range(len(acts)):
                if (S.stage[ai] >= 0).any():
                    resolve(ai, t)
            # 2a. exogenous events W(t): hazards outside the person's control
            for e in m.exogenous:
                if t + 1 <= e["start_week"] or (e["end_week"] is not None and t >= e["end_week"]):
                    continue
                key = "exo_" + e["id"]
                fired_e = S.token(key) > 0
                hz = self.P.value_or_param(e["hazard"])
                hit = (exo_u[e["id"]][t] < hz) & ~fired_e
                if e.get("unless_fn") is not None:
                    hit &= ~e["unless_fn"](cond_state)
                if hit.any():
                    S.token(key)[hit] = 1.0
                    for tk, dv in (e.get("tokens") or {}).items():
                        S.token(tk)[hit] += float(dv)
                    log(hit, t, "exogenous", None, e.get("label", e["id"]))
            # 2b. policy rules
            for ri, (f, r) in enumerate(rules):
                hit = f(cond_state) & ~fired[ri]
                if not hit.any():
                    continue
                fired[ri] |= hit
                log(hit, t, "rule", None, r.get("label", "rule fired"))
                for aid in r.get("enable", []):
                    if aid in S.idx:
                        i = S.idx[aid]
                        a = acts[i]
                        if a.requires_relocation and not self.sc.allow_relocation:
                            continue
                        S.status[i] = np.where(hit & (S.status[i] == OFF), TODO, S.status[i])
                        if aid not in prio:
                            prio[aid] = len(prio)
                for aid in r.get("disable", []):
                    if aid in S.idx:
                        i = S.idx[aid]
                        S.status[i] = np.where(hit & ((S.status[i] == TODO) | (S.status[i] == ACTIVE)), DROPPED,
                                               S.status[i])
            # 3. hours
            total = self.sc.weekly_hours * strat.hours_scale
            eff_total = effective_hours(total, self.sc.sustainable_cap)
            avail = np.full(n, max(eff_total - self.sc.academic_hours(t), 0.0))
            disrupted = u_disrupt[t] < disrupt_p
            avail = np.where(disrupted, avail * self.sc.disruption_hours_factor, avail)
            over = np.maximum(prev_active - self.sc.focus_k, 0)
            avail = avail * np.maximum(1 - self.sc.switch_cost * over, 0.5)
            remaining_h = avail.copy()
            # 4. allocation order: deadline-urgent first, then the strategy's priority
            live = [i for i, a in enumerate(acts) if a.id in prio]
            mean_avail = max(float(avail.mean()), 1e-6)

            def key(i):
                # Critical ratio: an action is urgent when the hours it still needs exceed
                # half of the hours available before its deadline (or it is due within 2 weeks).
                a = acts[i]
                if a.deadline_week is None:
                    return (1, 0.0, prio[a.id])
                st = S.status[i]
                live_mask = (st == TODO) | (st == ACTIVE)
                need = float(S.remaining[i][live_mask].mean()) if live_mask.any() else 0.0
                weeks_left = max(a.deadline_week - t, 1e-6)
                urgent = weeks_left < 2.0 or need > 0.5 * weeks_left * mean_avail
                return (0, a.deadline_week, prio[a.id]) if urgent else (1, 0.0, prio[a.id])
            live.sort(key=key)
            active_count = np.zeros(n)
            urgent_need = np.zeros(n)
            for i in live:
                a = acts[i]
                st = S.status[i]
                cand = ((st == TODO) | (st == ACTIVE)) & (t + 1 > a.start_week)
                if not cand.any():
                    continue
                ok = cand & a.requires(cond_state)
                cap = np.full(n, np.inf) if a.max_hours_week is None else np.full(n, float(a.max_hours_week))
                if a.deadline_week is not None:
                    frac = np.clip(a.deadline_week - t, 0.0, 1.0)
                    cap = np.minimum(cap, avail * frac) if frac < 1 else cap
                    if a.deadline_week - t < 2.0:
                        urgent_need += np.where(ok, S.remaining[i], 0.0)
                slot = (st == ACTIVE) | (active_count < strat.max_parallel)
                give = np.where(ok & slot, np.minimum(np.minimum(remaining_h, S.remaining[i]), cap), 0.0)
                got = give > 1e-9
                if got.any():
                    newly = got & (st == TODO)
                    S.started[i] = np.where(newly, t, S.started[i])
                    log(newly, t, "start", a, a.name)
                    S.status[i] = np.where(got, ACTIVE, S.status[i])
                    S.remaining[i] -= give
                    remaining_h -= give
                    active_count += got
                    hours_used += give
                done = got & (S.remaining[i] <= 1e-6)
                if done.any():
                    S.status[i] = np.where(done, DONE, S.status[i])
                    when = t + 1.0
                    S.completed[i] = np.where(done, when, S.completed[i])
                    log(done, when, "complete", a, a.name)
                    eff = a.effects
                    if eff:
                        apply_outcome(i, Outcome(label="effects", p=None, tokens=eff.get("tokens", {}),
                                                 metrics=eff.get("metrics", {})), done, np.ones(n), when)
                    for r in a.reveals:
                        S.token("known_" + r)[done] = 1.0
                        S.token(r)[done] = self.P[r][done]
                    if a.group:
                        for j, b in enumerate(acts):
                            if j != i and b.group == a.group:
                                drop = done & ((S.status[j] == TODO) | (S.status[j] == ACTIVE))
                                S.status[j] = np.where(drop, DROPPED, S.status[j])
                    if a.stages:
                        schedule_stage(i, 0, done, when)
            # 5. missed deadlines
            for i in live:
                a = acts[i]
                if a.deadline_week is not None and a.deadline_week < t + 1:
                    st = S.status[i]
                    miss = (st == TODO) | (st == ACTIVE)
                    if miss.any():
                        S.status[i] = np.where(miss, MISSED, st)
                        log(miss, a.deadline_week, "missed", a, a.name)
            crunch += (urgent_need > avail + 1e-9)
            prev_active = active_count
            if tw:
                for w in np.nonzero(disrupted[:tw])[0]:
                    trace.append({"world": int(w), "week": float(t), "type": "disruption", "action": None,
                                  "label": "Disrupted week (hours ×0.4)"})
            # time series
            pos = np.zeros(n, dtype=bool)
            for c, v in m.offer_classes.items():
                if v.get("position"):
                    pos |= offers[c]
            series["hours"].append(float((avail - remaining_h).mean()))
            series["position"].append(float(pos.mean()))
            series["peer_reviewed"].append(float(metrics["peer_reviewed"].mean()))
            series["public_outputs"].append(float(metrics["public_outputs"].mean()))
            series["crunch"].append(float((urgent_need > avail + 1e-9).mean()))
            series["offers_any"].append(float(np.logical_or.reduce([offers[c] for c in offers]).mean()))
            series["ties"].append(float(metrics["ties"].mean()))
            for c in offers:
                unlock_series.setdefault(c, []).append(float(offers[c].mean()))

        # final metrics
        pos_by_grad = np.zeros(n, dtype=bool)
        pos_any = np.zeros(n, dtype=bool)
        best_comp = np.zeros(n)
        autonomy = np.zeros(n)
        n_classes = np.zeros(n)
        for c, v in m.offer_classes.items():
            o = offers[c]
            n_classes += o
            autonomy = np.where(o, np.maximum(autonomy, float(v.get("autonomy", 0))), autonomy)
            if v.get("position"):
                pos_any |= o
                pos_by_grad |= o & (offer_week[c] <= m.graduation_week + 4)
                best_comp = np.where(o, np.maximum(best_comp, comp[c]), best_comp)
        new_collab = (S.token("collaborations") - float(m.initial_tokens.get("collaborations", 0)) > 0)
        optionality = n_classes + new_collab + (metrics["founder_stage"] >= 2)
        out_metrics = {
            "peer_reviewed": metrics["peer_reviewed"], "workshop": metrics["workshop"],
            "public_outputs": metrics["public_outputs"], "best_comp_lpa": best_comp,
            "position_by_grad": pos_by_grad.astype(float), "position_by_horizon": pos_any.astype(float),
            "optionality": optionality.astype(float), "autonomy": autonomy, "founder_stage": metrics["founder_stage"],
            "ties": metrics["ties"], "adoption": metrics["adoption"], "cash_lpa": metrics["cash_lpa"],
            "crunch_weeks": crunch, "hours_used": hours_used,
        }
        action_stats = {}
        for aid in prio:
            i = S.idx[aid]
            a = acts[i]
            st = S.status[i]
            comp_w = S.completed[i]
            outs = {}
            for si, stg in enumerate(a.stages):
                for oi, o in enumerate(stg.outcomes):
                    h = S.outcome_hits.get((i, si, oi))
                    outs[f"{stg.name} → {o.label}"] = float(h.mean()) if h is not None else 0.0
                h = S.outcome_hits.get((i, si, -1))
                outs[f"{stg.name} → {stg.otherwise.label}"] = float(h.mean()) if h is not None else 0.0
            action_stats[aid] = {
                "p_done": float((st == DONE).mean()), "p_missed": float((st == MISSED).mean()),
                "p_dropped": float((st == DROPPED).mean()), "p_never_enabled": float((st == OFF).mean()),
                "mean_completion_week": float(np.nanmean(comp_w)) if np.isfinite(comp_w).any() else None,
                "outcomes": outs,
            }
        return {
            "strategy": strat.id, "metrics": out_metrics, "series": series, "offer_series": unlock_series,
            "offers": {c: offers[c].astype(float) for c in offers},
            "offer_week": {c: offer_week[c] for c in offer_week},
            "action_stats": action_stats, "trace": trace, "unknown_actions": unknown,
            "params_drawn": {k: v for k, v in self.P.drawn.items()},
        }


class _CondView:
    """Adapter giving conditions the interface they expect (token(), status(), week, ones)."""
    DONE, MISSED, DROPPED = DONE, MISSED, DROPPED

    def __init__(self, S: State):
        self._S = S

    @property
    def ones(self):
        return self._S.ones

    @property
    def week(self):
        return self._S.week

    def token(self, name):
        return self._S.token(name)

    def status(self, aid):
        return self._S.status_of(aid)
