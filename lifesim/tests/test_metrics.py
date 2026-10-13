"""Expanded concrete metrics: money, time, stress, relationships, and diagnostics."""

import random

from lifesim.config import Config
from lifesim.dynamics import step
from lifesim.markets import update_investments
from lifesim.policy import DEFAULT_POLICY
from lifesim.simulate import simulate
from lifesim.state import ALL_VARS, OUTCOME_KEYS, initial_state, refresh_derived_metrics


def test_all_outcome_keys_exist_in_initial_state():
    state = initial_state("all", random.Random(1), jitter=False)
    assert set(OUTCOME_KEYS["all"]) <= set(state)
    assert "luck" not in OUTCOME_KEYS["all"]
    for key in ALL_VARS:
        assert key in state


def test_derived_money_and_diagnostics_refresh():
    state = initial_state(
        "all",
        random.Random(1),
        overrides={
            "cash_usd": 50000.0,
            "investments_usd": 25000.0,
            "debt_usd": 10000.0,
            "monthly_burn_usd": 5000.0,
        },
        jitter=False,
    )
    assert state["savings"] == 10.0
    assert state["net_worth_usd"] == 65000.0
    assert "monthly_investment_usd" in state
    assert "portfolio_return" in state
    for key in ("optionality", "luck_surface_area", "downside_fragility"):
        assert 0.0 <= state[key] <= 1.0


def test_investing_moves_excess_cash_into_marked_assets():
    state = initial_state(
        "all",
        random.Random(1),
        overrides={
            "cash_usd": 120000.0,
            "debt_usd": 0.0,
            "investments_usd": 20000.0,
            "monthly_burn_usd": 5000.0,
            "income_stability": 0.85,
            "market_sentiment": 0.65,
            "investment_exposure": 0.55,
            "portfolio_return": 0.0,
        },
        jitter=False,
    )
    next_state = dict(state)
    update_investments(state, next_state, DEFAULT_POLICY, 0.02, random.Random(2))
    assert next_state["monthly_investment_usd"] > 0.0
    assert next_state["cash_usd"] < state["cash_usd"]
    assert next_state["investments_usd"] > state["investments_usd"]


def test_market_returns_can_help_or_hurt_investments():
    state = initial_state(
        "all",
        random.Random(1),
        overrides={
            "cash_usd": 30000.0,
            "investments_usd": 100000.0,
            "market_sentiment": 0.50,
            "investment_exposure": 0.75,
            "portfolio_return": 0.0,
        },
        jitter=False,
    )
    returns = []
    for seed in range(80):
        next_state = dict(state)
        update_investments(state, next_state, DEFAULT_POLICY, 0.12, random.Random(seed))
        returns.append(next_state["portfolio_return"])
    assert min(returns) < 0.0
    assert max(returns) > 0.0


def test_trading_edge_adds_active_alpha_on_average():
    base = {
        "cash_usd": 90000.0,
        "investments_usd": 100000.0,
        "market_sentiment": 0.50,
        "investment_exposure": 0.75,
        "portfolio_return": 0.0,
        "stress": 0.25,
        "sleep_quality": 0.80,
        "career_leverage": 0.80,
        "income_stability": 0.75,
        "skill": 0.92,
    }
    low_edge = initial_state(
        "all", random.Random(1), overrides={**base, "trading_edge": 0.25}, jitter=False
    )
    high_edge = initial_state(
        "all", random.Random(1), overrides={**base, "trading_edge": 0.95}, jitter=False
    )
    low_returns = []
    high_returns = []
    for seed in range(120):
        low_next = dict(low_edge)
        high_next = dict(high_edge)
        update_investments(low_edge, low_next, DEFAULT_POLICY, 0.04, random.Random(seed))
        update_investments(high_edge, high_next, DEFAULT_POLICY, 0.04, random.Random(seed))
        low_returns.append(low_next["portfolio_return"])
        high_returns.append(high_next["portfolio_return"])
    assert sum(high_returns) / len(high_returns) > sum(low_returns) / len(low_returns) + 0.005


def test_net_worth_includes_market_moved_investments():
    state = initial_state(
        "all",
        random.Random(1),
        overrides={
            "cash_usd": 100000.0,
            "debt_usd": 12000.0,
            "investments_usd": 40000.0,
            "monthly_burn_usd": 5000.0,
        },
        jitter=False,
    )
    next_state = dict(state)
    update_investments(state, next_state, DEFAULT_POLICY, 0.02, random.Random(3))
    refresh_derived_metrics(next_state)
    assert next_state["net_worth_usd"] == (
        next_state["cash_usd"] + next_state["investments_usd"] - next_state["debt_usd"]
    )


def test_work_policy_raises_stress_and_hours_vs_health_policy():
    cfg = Config(domain="all", uncertainty=0.1, seed=4, horizon_months=6)
    rng_a = random.Random(4)
    rng_b = random.Random(4)
    start = initial_state("all", random.Random(3), jitter=False)
    work = dict(start)
    health = dict(start)
    for _ in range(cfg.horizon_months):
        work = step(work, {"work": 0.85, "love": 0.05, "health": 0.05, "explore": 0.05}, cfg, rng_a)
        health = step(health, {"work": 0.15, "love": 0.10, "health": 0.65, "explore": 0.10}, cfg, rng_b)
    assert work["work_hours_per_week"] > health["work_hours_per_week"]
    assert work["stress"] > health["stress"]
    assert work["burnout_risk"] > health["burnout_risk"]


def test_dummy_expanded_scenario_runs_all_metrics():
    cfg = Config(domain="all", uncertainty=0.2, seed=9, horizon_months=6, n_min=20, n_max=20)
    overrides = {
        "cash_usd": 80000.0,
        "debt_usd": 12000.0,
        "investments_usd": 45000.0,
        "annual_income_usd": 110000.0,
        "monthly_burn_usd": 6500.0,
        "work_hours_per_week": 50.0,
        "sleep_hours": 6.5,
        "stress": 0.55,
        "romantic_connection": 0.35,
        "friendship_depth": 0.45,
        "fitness": 0.50,
    }
    res = simulate(cfg, DEFAULT_POLICY, overrides=overrides, jitter=False)
    for key in (
        "net_worth_usd", "annual_income_usd", "monthly_investment_usd",
        "portfolio_return", "active_trading_alpha", "trading_edge",
        "market_sentiment", "burnout_risk", "loneliness",
    ):
        assert key in res.keys
        assert key in res.bands
        assert len(res.bands[key]) == cfg.horizon_months + 1
