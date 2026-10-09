"""Synthetic scenarios with known answers (PROJECT brief Part 15.5).

Each test builds a tiny model in code, runs the real engine, and compares against an
analytic result. Tolerances are set from Monte Carlo standard errors.
"""
import math
from datetime import datetime

import numpy as np
import pytest

from horizon.sim.analysis import check_constraints, evaluate, evppi, utility
from horizon.sim.engine import Scenario, Simulator, Strategy
from horizon.sim.model import IST, Model, build_action, validate_model
from horizon.sim.params import Dist, Param

START = datetime(2026, 10, 9, tzinfo=IST)


def P(name, dist, origin="illustrative_placeholder"):
    return Param(name=name, dist=Dist.parse(dist), origin=origin)


def mk(actions, params=(), offers=None, initial=None, horizon=20):
    ps = {p.name: p for p in params}
    ps.setdefault("effort_noise_gsd", P("effort_noise_gsd", "fixed(1)"))
    ps.setdefault("p_disruption_week", P("p_disruption_week", "fixed(0)"))
    acts = []
    for a in actions:
        acts.extend(build_action(a, START))
    m = Model(start=START, horizon_weeks=horizon, graduation_week=horizon, actions=acts, params=ps,
              offer_classes=offers or {}, initial_tokens=initial or {})
    validate_model(m)
    return m


def flat(hours=40.0, **kw):
    return Scenario(name="test", weekly_hours=hours, ai_multiplier=1.0, effort_bias=1.0, sustainable_cap=1e9,
                    switch_cost=0.0, academic=[], factor_corr=0.0, **kw)


def run(m, strat, sc=None, n=4000, seed=1):
    return Simulator(m, sc or flat(), n_worlds=n, seed=seed).run(strat)


def S(*acts, rules=(), contingent=(), max_parallel=10):
    return Strategy(id="s", name="s", actions=list(acts), rules=list(rules), contingent=list(contingent),
                    max_parallel=max_parallel)


def test_deterministic_plan_completes_on_schedule():
    m = mk([{"id": "a", "name": "A", "effort": [50, 50, 50], "effects": {"tokens": {"x": 1}}}])
    r = run(m, S("a"), n=50)
    st = r["action_stats"]["a"]
    assert st["p_done"] == 1.0
    assert st["mean_completion_week"] == 2.0  # 40 h in week 0, last 10 h in week 1 → done at end of week 1


def test_two_action_bayesian_decision_matches_analytic_expectation():
    # A succeeds with p ~ Beta(3,7) (mean 0.3) worth 10; B with fixed p 0.5 worth 5.
    acts = [
        {"id": "a", "name": "A", "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "win", "p": {"base": "pa"}, "metrics": {"cash_lpa": 10}}], "otherwise": {"label": "no"}}]},
        {"id": "b", "name": "B", "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "win", "p": {"base": "pb"}, "metrics": {"cash_lpa": 5}}], "otherwise": {"label": "no"}}]},
    ]
    m = mk(acts, [P("pa", "beta(3, 7)"), P("pb", "fixed(0.5)")])
    ra, rb = run(m, S("a"), n=20000), run(m, S("b"), n=20000)
    ea, eb = ra["metrics"]["cash_lpa"].mean(), rb["metrics"]["cash_lpa"].mean()
    se_a = ra["metrics"]["cash_lpa"].std() / math.sqrt(20000)
    assert abs(ea - 3.0) < 4 * se_a
    assert abs(eb - 2.5) < 4 * rb["metrics"]["cash_lpa"].std() / math.sqrt(20000)
    assert ea > eb


def test_resource_constraint_forces_a_choice_by_priority():
    acts = [{"id": "a", "name": "A", "effort": [30, 30, 30], "deadline": "2026-10-16T00:00:00+05:30"},
            {"id": "b", "name": "B", "effort": [30, 30, 30], "deadline": "2026-10-16T00:00:00+05:30"}]
    m = mk(acts)
    r = run(m, S("a", "b"), n=20)
    assert r["action_stats"]["a"]["p_done"] == 1.0
    assert r["action_stats"]["b"]["p_missed"] == 1.0
    r2 = run(m, S("b", "a"), n=20)
    assert r2["action_stats"]["b"]["p_done"] == 1.0 and r2["action_stats"]["a"]["p_missed"] == 1.0


def test_and_or_prerequisites_reachability():
    acts = [
        {"id": "a", "name": "A", "effort": [1, 1, 1], "effects": {"tokens": {"ta": 1}}},
        {"id": "b", "name": "B", "effort": [1, 1, 1], "effects": {"tokens": {"tb": 1}}},
        {"id": "both", "name": "AND", "effort": [1, 1, 1],
         "requires": {"all": [{"token": "ta"}, {"token": "tb"}]}},
        {"id": "either", "name": "OR", "effort": [1, 1, 1],
         "requires": {"any": [{"token": "ta"}, {"token": "tb"}]}},
    ]
    m = mk(acts)
    r = run(m, S("a", "both", "either"), n=10)
    assert r["action_stats"]["either"]["p_done"] == 1.0
    assert r["action_stats"]["both"]["p_done"] == 0.0  # B never done → AND unreachable
    r = run(m, S("a", "b", "both"), n=10)
    assert r["action_stats"]["both"]["p_done"] == 1.0


def test_independent_binomial_batch():
    acts = [{"id": "a", "name": "A", "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
        {"label": "hit", "count": 10, "p": {"base": "p"}, "tokens": {"k": 1}}], "otherwise": {"label": "none"}}]},
        {"id": "z", "name": "probe", "effort": [1, 1, 1], "start": "2026-11-20",
         "requires": {"token": "k", "op": ">=", "value": 1}}]
    m = mk(acts, [P("p", "fixed(0.2)")])
    r = run(m, S("a", "z"), n=20000)
    p_any = 1 - 0.8 ** 10
    assert abs(r["action_stats"]["z"]["p_done"] - p_any) < 0.012


def _two_apps(load):
    out = {"label": "offer", "p": {"base": "p", "factors": {"portfolio": load}}}
    return [{"id": i, "name": i, "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
        {**out, "tokens": {f"o_{i}": 1}}], "otherwise": {"label": "no"}}]} for i in ("x", "y")]


def test_latent_factor_induces_positive_correlation():
    corr = {}
    for load in (0.0, 1.5):
        m = mk(_two_apps(load), [P("p", "fixed(0.3)")])
        sim = Simulator(m, flat(), n_worlds=20000, seed=3)
        st = sim.run(S("x", "y"))
        # recover per-world tokens through action outcome hits
        hx = st["action_stats"]["x"]["outcomes"]["r → offer"]
        both = None
        # re-run with tracing of tokens: use the metrics-free path by reading state via a third action
        m2 = mk(_two_apps(load) + [{"id": "j", "name": "joint", "effort": [1, 1, 1], "start": "2026-11-20",
                                    "requires": {"all": [{"token": "o_x"}, {"token": "o_y"}]}}],
                [P("p", "fixed(0.3)")])
        both = Simulator(m2, flat(), n_worlds=20000, seed=3).run(S("x", "y", "j"))["action_stats"]["j"]["p_done"]
        corr[load] = (hx, both)
    px0, both0 = corr[0.0]
    assert abs(both0 - px0 ** 2) < 0.015          # independence
    px1, both1 = corr[1.5]
    assert both1 > px1 ** 2 + 0.03                # positive dependence


def test_information_changes_the_optimal_decision():
    # theta ~ Bernoulli(0.5). Strategy A pays 10 if theta=1 else 0. Strategy B pays 4 always.
    # EU(A)=5 > EU(B)=4, but knowing theta yields 0.5*10 + 0.5*4 = 7 → EVPPI = 2.
    acts = [
        {"id": "a", "name": "A", "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "pay", "p": {"base": "theta"}, "metrics": {"cash_lpa": 10}}], "otherwise": {"label": "no"}}]},
        {"id": "b", "name": "B", "effort": [1, 1, 1], "effects": {"metrics": {"cash_lpa": 4}}},
    ]
    m = mk(acts, [P("theta", "bernoulli(0.5)")])
    sim = Simulator(m, flat(), n_worlds=8000, seed=5)
    ra, rb = sim.run(S("a")), sim.run(S("b"))
    U = {"a": ra["metrics"]["cash_lpa"], "b": rb["metrics"]["cash_lpa"]}
    theta = sim.P["theta"]
    res = evppi(U, theta)
    assert abs(res["evppi"] - 2.0) < 0.3
    assert res["decision_sensitive"]
    assert set(res["best_by_bin"]) == {"a", "b"}


def test_shortest_path_is_not_the_best_strategy():
    acts = [
        {"id": "short", "name": "short", "effort": [5, 5, 5], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "ok", "p": {"base": "ps"}, "metrics": {"cash_lpa": 1}}],
            "otherwise": {"label": "no"}}]},
        {"id": "long", "name": "long", "effort": [60, 60, 60], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "ok", "p": {"base": "pl"}, "metrics": {"cash_lpa": 1}}], "otherwise": {"label": "no"}}]},
    ]
    m = mk(acts, [P("ps", "fixed(0.2)"), P("pl", "fixed(0.8)")])
    rs, rl = run(m, S("short")), run(m, S("long"))
    assert rs["action_stats"]["short"]["mean_completion_week"] < rl["action_stats"]["long"]["mean_completion_week"]
    assert rl["metrics"]["cash_lpa"].mean() > rs["metrics"]["cash_lpa"].mean() + 0.5


def test_two_simultaneous_prerequisites_multiply():
    acts = [
        {"id": i, "name": i, "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
            {"label": "ok", "p": {"base": f"p{i}"}, "tokens": {f"t{i}": 1}}], "otherwise": {"label": "no"}}]}
        for i in ("a", "b")
    ] + [{"id": "goal", "name": "goal", "effort": [1, 1, 1], "start": "2026-11-20",
          "requires": {"all": [{"token": "ta"}, {"token": "tb"}]}}]
    m = mk(acts, [P("pa", "fixed(0.6)"), P("pb", "fixed(0.5)")])
    r = run(m, S("a", "b", "goal"), n=20000)
    assert abs(r["action_stats"]["goal"]["p_done"] - 0.30) < 0.015


def test_hard_constraint_rejects_higher_value_option():
    rng = np.random.default_rng(0)
    n = 1000
    results = {
        "risky": {"metrics": {"cash_lpa": rng.normal(10, 1, n), "position_by_grad": (rng.random(n) < 0.5) * 1.0}},
        "safe": {"metrics": {"cash_lpa": rng.normal(6, 1, n), "position_by_grad": (rng.random(n) < 0.95) * 1.0}},
    }
    prof = {"weights": {"cash_lpa": 1.0}, "risk": {"measure": "mean"},
            "constraints": [{"metric": "position_by_grad", "stat": "mean", "op": ">=", "value": 0.8, "hard": True}]}
    ev = evaluate(results, prof, {"refs": {"cash_lpa": 1}, "caps": {"cash_lpa": 100}})
    assert ev["ranking"][0]["strategy"] == "safe"
    assert not [r for r in ev["ranking"] if r["strategy"] == "risky"][0]["feasible"]


def test_reproducible_with_same_seed_and_common_random_numbers():
    acts = [{"id": "a", "name": "A", "effort": [5, 10, 30], "stages": [{"name": "r", "delay": "d", "outcomes": [
        {"label": "ok", "p": {"base": "p"}, "metrics": {"cash_lpa": 1}}], "otherwise": {"label": "no"}}]}]
    m = mk(acts, [P("p", "beta(2, 5)"), P("d", "triangular(1, 2, 4)"),
                  P("effort_noise_gsd", "fixed(1.3)"), P("p_disruption_week", "fixed(0.05)")])
    r1 = run(m, S("a"), n=500, seed=42)
    r2 = run(m, S("a"), n=500, seed=42)
    r3 = run(m, S("a"), n=500, seed=43)
    assert np.array_equal(r1["metrics"]["cash_lpa"], r2["metrics"]["cash_lpa"])
    assert not np.array_equal(r1["metrics"]["cash_lpa"], r3["metrics"]["cash_lpa"])
    assert np.array_equal(r1["params_drawn"]["p"], r2["params_drawn"]["p"])


def test_fractional_deadline_week_caps_hours():
    # deadline half-way through week 0: 40 h/week available → 20 h before the deadline
    acts = [{"id": "a", "name": "A", "effort": [25, 25, 25], "deadline": "2026-10-12T12:00:00+05:30"},
            {"id": "b", "name": "B", "effort": [15, 15, 15], "deadline": "2026-10-12T12:00:00+05:30"}]
    m = mk(acts)
    assert run(m, S("a"), n=10)["action_stats"]["a"]["p_missed"] == 1.0
    assert run(m, S("b"), n=10)["action_stats"]["b"]["p_done"] == 1.0


def test_rules_enable_contingent_action_after_a_miss():
    acts = [{"id": "a", "name": "A", "effort": [100, 100, 100], "deadline": "2026-10-12T12:00:00+05:30",
             "group": "g"},
            {"id": "a2", "name": "A later", "effort": [10, 10, 10], "group": "g"}]
    m = mk(acts)
    r = run(m, S("a", rules=[{"when": {"missed": "a"}, "enable": ["a2"]}], contingent=["a2"]), n=10)
    assert r["action_stats"]["a"]["p_missed"] == 1.0
    assert r["action_stats"]["a2"]["p_done"] == 1.0


def test_monte_carlo_error_shrinks_with_n():
    acts = [{"id": "a", "name": "A", "effort": [1, 1, 1], "stages": [{"name": "r", "delay": 1, "outcomes": [
        {"label": "ok", "p": {"base": "p"}, "metrics": {"cash_lpa": 1}}], "otherwise": {"label": "no"}}]}]
    m = mk(acts, [P("p", "beta(2, 2)")])
    errs = []
    for n in (500, 8000):
        means = [run(m, S("a"), n=n, seed=s)["metrics"]["cash_lpa"].mean() for s in range(12)]
        errs.append(np.std(means))
    assert errs[1] < errs[0] / 2.5   # ~1/sqrt(16) = 0.25


def test_utility_saturates_and_respects_negative_weights():
    met = {"x": np.array([0.0, 1.0, 10.0]), "c": np.array([0.0, 6.0, 12.0])}
    u = utility(met, {"weights": {"x": 1.0, "c": -1.0}}, {"refs": {"x": 1, "c": 6}, "caps": {"x": 2, "c": 3}})
    assert np.allclose(u, [0.0, 0.0, 2.0 - 2.0])


def test_constraint_checking_statistics():
    met = {"m": np.arange(100, dtype=float)}
    out = check_constraints(met, [{"metric": "m", "stat": "p90", "op": "<=", "value": 89.5}])
    assert out[0]["observed"] == pytest.approx(89.1)
    assert out[0]["satisfied"]


def test_model_rejects_writes_to_derived_metrics():
    with pytest.raises(ValueError, match="derived metric"):
        mk([{"id": "a", "name": "A", "effort": [1, 1, 1], "effects": {"metrics": {"position_by_grad": 1}}}])


def test_probability_evaluated_at_resolution_sees_later_state():
    # The paper is submitted in week 0; a registration that lands two days later must still count
    # when the desk check resolves, but not when the probability is frozen at submission.
    def acts(at):
        return [
            {"id": "paper", "name": "paper", "effort": [1, 1, 1], "stages": [{"name": "desk", "delay": 1, "outcomes": [
                {"label": "ok", "p": {"base": "p", "shifts": [{"param": "pen", "token": "missing", "cap": 1}], "at": at},
                 "tokens": {"passed": 1}}], "otherwise": {"label": "rejected"}}]},
            {"id": "reg", "name": "register", "effort": [1, 1, 1], "start": "2026-10-11",
             "effects": {"tokens": {"missing": -1}}},
        ]
    params = [P("p", "fixed(0.95)"), P("pen", "fixed(-10)")]
    frozen = run(mk(acts("start"), params, initial={"missing": 1}), S("paper", "reg"), n=2000)
    live = run(mk(acts("resolve"), params, initial={"missing": 1}), S("paper", "reg"), n=2000)
    assert frozen["action_stats"]["paper"]["outcomes"]["desk → ok"] < 0.01
    assert abs(live["action_stats"]["paper"]["outcomes"]["desk → ok"] - 0.95) < 0.02
