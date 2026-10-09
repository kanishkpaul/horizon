"""Condition DSL used for prerequisites and policy rules.

A condition is evaluated for all simulated worlds at once and returns a boolean array.

    {token: name, op: ">=", value: 1}      token comparison (ops: >= > <= < == !=)
    {done: action_id} / {failed: action_id} / {missed: action_id}
    {week_ge: 10} / {week_lt: 20}
    {all: [cond, ...]} / {any: [cond, ...]} / {not: cond}
    null                                   always true
"""
from __future__ import annotations

import operator
from typing import Callable

import numpy as np

OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq, "!=": operator.ne}


def compile_cond(c) -> Callable:
    if c is None:
        return lambda s: s.ones
    if not isinstance(c, dict) or len(c) == 0:
        raise ValueError(f"bad condition: {c!r}")
    if "token" in c:
        name, op, val = c["token"], OPS[c.get("op", ">=")], float(c.get("value", 1))
        return lambda s: op(s.token(name), val)
    if "done" in c:
        a = c["done"]
        return lambda s: s.status(a) == s.DONE
    if "failed" in c:
        a = c["failed"]
        return lambda s: (s.status(a) == s.MISSED) | (s.status(a) == s.DROPPED)
    if "missed" in c:
        a = c["missed"]
        return lambda s: s.status(a) == s.MISSED
    if "week_ge" in c:
        w = float(c["week_ge"])
        return lambda s: s.ones & (s.week >= w)
    if "week_lt" in c:
        w = float(c["week_lt"])
        return lambda s: s.ones & (s.week < w)
    if "all" in c:
        fs = [compile_cond(x) for x in c["all"]]
        return lambda s: np.logical_and.reduce([f(s) for f in fs]) if fs else s.ones
    if "any" in c:
        fs = [compile_cond(x) for x in c["any"]]
        return lambda s: np.logical_or.reduce([f(s) for f in fs]) if fs else ~s.ones
    if "not" in c:
        f = compile_cond(c["not"])
        return lambda s: ~f(s)
    raise ValueError(f"bad condition: {c!r}")


def describe(c) -> str:
    """Human-readable rendering for explanations."""
    if c is None:
        return "always"
    if "token" in c:
        return f"{c['token']} {c.get('op', '>=')} {c.get('value', 1)}"
    for k in ("done", "failed", "missed"):
        if k in c:
            return f"{c[k]} {k}"
    if "week_ge" in c:
        return f"week ≥ {c['week_ge']}"
    if "week_lt" in c:
        return f"week < {c['week_lt']}"
    if "all" in c:
        return " and ".join(f"({describe(x)})" for x in c["all"])
    if "any" in c:
        return " or ".join(f"({describe(x)})" for x in c["any"])
    if "not" in c:
        return f"not ({describe(c['not'])})"
    return str(c)
