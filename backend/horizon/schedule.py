"""Day-level schedule for the next N days with OR-Tools CP-SAT.

Decision variables are half-hour blocks of each open action on each day. Constraints:
daily capacity, nothing after an action's due date, at most the action's remaining effort.
Objective (lexicographic via weights): schedule as much required work as possible before its
due date, then prefer earlier work, then keep the number of distinct tasks per day ≤ 2
(context switching). Unschedulable work is reported, not hidden.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ortools.sat.python import cp_model

from .db import rows

IST = timezone(timedelta(hours=5, minutes=30))


def plan_days(con, days: int = 14, weekday_hours: float = 5.0, weekend_hours: float = 9.0,
              max_tasks_per_day: int = 2, start: date | None = None) -> dict:
    start = start or datetime.now(IST).date()
    horizon_end = start + timedelta(days=days - 1)
    items = rows(con, "SELECT * FROM action_item WHERE status IN ('todo','doing') ORDER BY due")
    tasks = []
    for it in items:
        due = date.fromisoformat(it["due"]) if it.get("due") else None
        if due and due < start:
            continue
        effort = float(it.get("effort_hours") or 0)
        if effort <= 0:
            continue
        # only actions due inside the window must finish; later ones may be started early
        must = due is not None and due <= horizon_end
        if not must and len(tasks) >= 12:
            continue
        tasks.append({"id": it["id"], "title": it["title"], "due": due, "effort": effort, "must": must})
    day_list = [start + timedelta(days=i) for i in range(days)]
    cap = [int(2 * (weekend_hours if d.weekday() >= 5 else weekday_hours)) for d in day_list]
    m = cp_model.CpModel()
    x, y = {}, {}
    for ti, t in enumerate(tasks):
        blocks = int(round(2 * t["effort"]))
        for di, d in enumerate(day_list):
            ub = 0 if (t["due"] and d > t["due"]) else min(cap[di], blocks)
            x[ti, di] = m.NewIntVar(0, ub, f"x{ti}_{di}")
            y[ti, di] = m.NewBoolVar(f"y{ti}_{di}")
            m.Add(x[ti, di] == 0).OnlyEnforceIf(y[ti, di].Not())
            m.Add(x[ti, di] >= 1).OnlyEnforceIf(y[ti, di])
        m.Add(sum(x[ti, di] for di in range(days)) <= blocks)
    over = []
    for di in range(days):
        m.Add(sum(x[ti, di] for ti in range(len(tasks))) <= cap[di])
        o = m.NewIntVar(0, len(tasks), f"over{di}")
        m.Add(o >= sum(y[ti, di] for ti in range(len(tasks))) - max_tasks_per_day)
        over.append(o)
    must_done = sum(x[ti, di] for ti, t in enumerate(tasks) if t["must"] for di in range(days))
    any_done = sum(x[ti, di] for ti in range(len(tasks)) for di in range(days))
    earliness = sum(di * x[ti, di] for ti in range(len(tasks)) for di in range(days))
    m.Maximize(10_000 * must_done + 100 * any_done - earliness - 50 * sum(over))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_workers = 8
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "days": [], "unscheduled": tasks}
    out_days = []
    for di, d in enumerate(day_list):
        slots = [{"id": t["id"], "title": t["title"], "hours": solver.Value(x[ti, di]) / 2}
                 for ti, t in enumerate(tasks) if solver.Value(x[ti, di]) > 0]
        out_days.append({"date": d.isoformat(), "capacity_h": cap[di] / 2, "tasks": slots})
    unsched = []
    for ti, t in enumerate(tasks):
        got = sum(solver.Value(x[ti, di]) for di in range(days)) / 2
        if t["must"] and got + 1e-9 < t["effort"]:
            unsched.append({"id": t["id"], "title": t["title"], "short_by_h": round(t["effort"] - got, 1),
                            "due": t["due"].isoformat() if t["due"] else None})
    return {"status": "optimal" if status == cp_model.OPTIMAL else "feasible", "days": out_days,
            "unscheduled": unsched, "assumptions": {"weekday_hours": weekday_hours, "weekend_hours": weekend_hours,
                                                    "max_tasks_per_day": max_tasks_per_day},
            "method": "CP-SAT: maximise required work before due dates, then total work, prefer earlier days, "
                      "penalise more than the task-per-day limit."}
