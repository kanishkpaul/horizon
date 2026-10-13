"""Investment and market dynamics.

Money only becomes net worth honestly if it has a place to live. This module
models that place: excess cash can move into investments, then investments rise
or fall with a noisy market. It is intentionally small and scenario-level, not a
finance engine; the goal is to make the wealth path less fake, not to predict
markets.
"""

from __future__ import annotations

import random

from .state import clamp01


def _noise(rng: random.Random, scale: float, sd: float) -> float:
    return rng.gauss(0.0, scale * sd)


def update_investments(
    state: dict,
    s: dict,
    policy: dict,
    ns: float,
    rng: random.Random,
) -> None:
    """Move excess cash into investments, then mark investments to market.

    `state` is the previous month and `s` is the next month under construction.
    The cash transfer is conservative: keep roughly six months of burn as an
    emergency bucket, pay down debt pressure first, then invest some of the
    remaining cash. Market sentiment is a bounded latent-ish state; portfolio
    return is the visible monthly return applied to invested assets.
    """
    burn = max(1.0, s["monthly_burn_usd"])
    debt_load = clamp01(s["debt_usd"] / 50000.0)
    runway = clamp01(s["cash_usd"] / burn / 12.0)
    explore = policy["explore"]
    work = policy["work"]
    stress = s.get("stress", state.get("stress", 0.5))
    sleep_quality = s.get("sleep_quality", state.get("sleep_quality", 0.5))

    target_exposure = clamp01(
        0.18 + 0.26 * s["income_stability"] + 0.22 * runway
        + 0.16 * explore + 0.08 * work + 0.18 * state["trading_edge"]
        - 0.24 * debt_load
    )
    s["investment_exposure"] = clamp01(
        state["investment_exposure"]
        + 0.16 * (target_exposure - state["investment_exposure"])
        + _noise(rng, ns, 0.22)
    )

    target_edge = clamp01(
        0.30 * s["skill"] + 0.22 * s["career_leverage"]
        + 0.18 * s["income_stability"] + 0.14 * explore
        + 0.10 * sleep_quality + 0.06 * state["trading_edge"]
        - 0.14 * stress
    )
    s["trading_edge"] = clamp01(
        state["trading_edge"]
        + 0.08 * (target_edge - state["trading_edge"])
        + _noise(rng, ns, 0.18)
    )

    prior_return = state["portfolio_return"]
    sentiment_pull = 0.09 * (0.52 - state["market_sentiment"])
    momentum = 0.55 * max(-0.04, min(0.04, prior_return))
    s["market_sentiment"] = clamp01(
        state["market_sentiment"] + sentiment_pull + momentum
        + _noise(rng, ns, 0.55)
    )

    shock = 0.0
    shock_chance = 0.004 + 0.06 * ns
    if rng.random() < shock_chance:
        shock = -(0.08 + 0.18 * rng.random())
        s["market_sentiment"] = clamp01(s["market_sentiment"] - 0.20)
    elif rng.random() < shock_chance * 0.8:
        shock = 0.06 + 0.12 * rng.random()
        s["market_sentiment"] = clamp01(s["market_sentiment"] + 0.15)

    edge_above_average = max(0.0, s["trading_edge"] - 0.50)
    alpha_mean = 0.030 * edge_above_average * s["investment_exposure"] \
        - 0.010 * stress - 0.006 * max(0.0, 0.55 - sleep_quality)
    alpha_vol = 0.006 + 0.030 * s["investment_exposure"] \
        + 0.025 * (1.0 - s["trading_edge"]) + 0.010 * stress
    s["active_trading_alpha"] = max(
        -0.35,
        min(0.35, rng.gauss(alpha_mean, alpha_vol * (0.45 + 3.0 * ns))),
    )

    expected_market = -0.004 + 0.017 * s["market_sentiment"]
    volatility = 0.010 + 0.050 * s["investment_exposure"] \
        + 0.015 * (1.0 - s["market_sentiment"])
    s["portfolio_return"] = (
        s["investment_exposure"] * expected_market
        + s["active_trading_alpha"]
        + rng.gauss(0.0, volatility * (0.45 + 4.0 * ns))
        + shock
    )

    emergency_cash = 6.0 * burn
    investable_cash = max(0.0, s["cash_usd"] - emergency_cash)
    contribution_rate = clamp01(
        0.10 + 0.55 * s["investment_exposure"]
        + 0.10 * s["income_stability"] - 0.30 * debt_load
    )
    contribution = min(investable_cash, investable_cash * contribution_rate)
    s["monthly_investment_usd"] = contribution
    s["cash_usd"] -= contribution

    marked_assets = state["investments_usd"] * (1.0 + s["portfolio_return"])
    s["investments_usd"] = max(0.0, marked_assets + contribution)
