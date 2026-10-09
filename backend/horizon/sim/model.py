"""Compile the declarative catalog (YAML + database shortlist) into executable specs."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .conditions import compile_cond, describe
from .params import Dist, Param

MODEL_VERSION = "horizon-sim 0.3.0"
# outcome metrics an action may write; derived metrics (best_comp_lpa, position_by_grad, ...) are computed
SUM_METRICS = ("peer_reviewed", "workshop", "public_outputs", "ties", "adoption", "cash_lpa")
MAX_METRICS = ("founder_stage",)
IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class ProbSpec:
    base: object                     # parameter name or {"dist": ...}
    shifts: list = field(default_factory=list)   # [{"param":..., "token":..., "cap":...}]
    factors: dict = field(default_factory=dict)  # factor -> loading (number or parameter name)
    at: str = "start"   # "start": frozen when the stage begins (evidence at submission); "resolve": state at decision


@dataclass
class Outcome:
    label: str
    p: ProbSpec | None
    count: int | None = None
    tokens: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)


@dataclass
class Stage:
    name: str
    delay: object
    outcomes: list[Outcome]
    otherwise: Outcome


@dataclass
class Action:
    id: str
    name: str
    kind: str
    effort: tuple[float, float, float]
    automatable: float
    start_week: float = 0.0
    deadline_week: float | None = None
    deadline_iso: str | None = None
    deadline_basis: str | None = None
    max_hours_week: float | None = None
    group: str | None = None
    requires_spec: object = None
    effects: dict = field(default_factory=dict)
    stages: list[Stage] = field(default_factory=list)
    reveals: list[str] = field(default_factory=list)
    requires_relocation: bool = False
    external_dependency: str | None = None
    opportunity_id: str | None = None
    template: str | None = None

    def __post_init__(self):
        self.requires = compile_cond(self.requires_spec)

    def describe(self) -> dict:
        return {
            "id": self.id, "name": self.name, "kind": self.kind, "effort": list(self.effort),
            "automatable": self.automatable, "start_week": self.start_week, "deadline_week": self.deadline_week,
            "deadline": self.deadline_iso, "deadline_basis": self.deadline_basis, "group": self.group,
            "requires": describe(self.requires_spec), "requires_spec": self.requires_spec,
            "effects": self.effects, "reveals": self.reveals, "requires_relocation": self.requires_relocation,
            "external_dependency": self.external_dependency, "opportunity_id": self.opportunity_id,
            "stages": [
                {"name": s.name, "delay": s.delay,
                 "outcomes": [{"label": o.label, "count": o.count, "tokens": o.tokens, "metrics": o.metrics,
                               "p": None if o.p is None else {"base": o.p.base, "shifts": o.p.shifts,
                                                              "factors": o.p.factors, "at": o.p.at}}
                              for o in s.outcomes],
                 "otherwise": {"label": s.otherwise.label, "tokens": s.otherwise.tokens}}
                for s in self.stages
            ],
        }


@dataclass
class Model:
    start: datetime
    horizon_weeks: int
    graduation_week: float
    actions: list[Action]
    params: dict[str, Param]
    offer_classes: dict
    initial_tokens: dict
    factors: tuple[str, ...] = ("portfolio", "market")
    exogenous: list = field(default_factory=list)   # W(t): hazards outside the person's control
    version: str = MODEL_VERSION

    def action(self, aid: str) -> Action:
        for a in self.actions:
            if a.id == aid:
                return a
        raise KeyError(aid)

    def fingerprint(self) -> str:
        blob = json.dumps({
            "actions": [a.describe() for a in self.actions],
            "params": {k: [str(p.dist), p.origin] for k, p in sorted(self.params.items())},
            "offers": self.offer_classes, "init": self.initial_tokens, "v": self.version,
            "exo": [{k: v for k, v in e.items() if k != "unless_fn"} for e in self.exogenous],
        }, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]

    def week_of(self, d) -> float:
        return to_week(self.start, d)

    def date_of(self, week: float) -> str:
        return (self.start + timedelta(weeks=week)).astimezone(IST).date().isoformat()


def to_week(start: datetime, d) -> float:
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace("Z", "+00:00")) if "T" in d else datetime.combine(
            date.fromisoformat(d), datetime.min.time(), IST)
    elif isinstance(d, date) and not isinstance(d, datetime):
        d = datetime.combine(d, datetime.min.time(), IST)
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return (d - start).total_seconds() / (7 * 86400)


def _prob(spec) -> ProbSpec | None:
    if spec is None:
        return None
    if isinstance(spec, (str, int, float)):
        return ProbSpec(base=spec)
    shifts = []
    for s in spec.get("shifts", []) or []:
        shifts.append({"param": s} if isinstance(s, str) else dict(s))
    at = spec.get("at", "start")
    if at not in ("start", "resolve"):
        raise ValueError(f"bad probability timing {at!r}")
    if "dist" in spec:
        return ProbSpec(base={"dist": spec["dist"]}, shifts=shifts, factors=dict(spec.get("factors") or {}), at=at)
    return ProbSpec(base=spec["base"], shifts=shifts, factors=dict(spec.get("factors") or {}), at=at)


def _outcome(o: dict | None, default_label="Otherwise") -> Outcome:
    o = o or {}
    return Outcome(label=o.get("label", default_label), p=_prob(o.get("p")), count=o.get("count"),
                   tokens=dict(o.get("tokens") or {}), metrics=dict(o.get("metrics") or {}))


def _sub(obj, i: int):
    """Replace the "$i" placeholder used by multi-instance actions."""
    if isinstance(obj, dict):
        return {k: _sub(v, i) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sub(v, i) for v in obj]
    if obj == "$i":
        return i
    return obj


def build_action(raw: dict, start: datetime) -> list[Action]:
    n = int(raw.get("instances", 1))
    out = []
    for i in range(1, n + 1):
        r = _sub(copy.deepcopy(raw), i)
        aid = r["id"] if n == 1 else f"{r['id']}_{i}"
        name = r["name"] if n == 1 else f"{r['name']} (#{i})"
        stages = []
        for s in r.get("stages", []) or []:
            stages.append(Stage(name=s.get("name", "Response"), delay=s.get("delay", 0),
                                outcomes=[_outcome(o) for o in s.get("outcomes", [])],
                                otherwise=_outcome(s.get("otherwise"), "Otherwise")))
        dl = r.get("deadline")
        out.append(Action(
            id=aid, name=name, kind=r.get("kind", "other"), effort=tuple(float(x) for x in r["effort"]),
            automatable=float(r.get("automatable", 0.0)),
            start_week=max(0.0, to_week(start, r["start"])) if r.get("start") else 0.0,
            deadline_week=to_week(start, dl) if dl else None, deadline_iso=dl,
            deadline_basis=r.get("deadline_basis"), max_hours_week=r.get("max_hours_week"),
            group=r.get("group"), requires_spec=r.get("requires"), effects=dict(r.get("effects") or {}),
            stages=stages, reveals=list(r.get("reveals") or []), requires_relocation=bool(r.get("requires_relocation")),
            external_dependency=r.get("external_dependency"), opportunity_id=r.get("opportunity_id"),
            template=r.get("template"),
        ))
    return out


def compile_exogenous(e: dict, start: datetime) -> dict:
    """{id, label, hazard (weekly probability: number or parameter), unless (condition), tokens, start, end}."""
    out = dict(e)
    out["start_week"] = max(0.0, to_week(start, e["start"])) if e.get("start") else 0.0
    out["end_week"] = to_week(start, e["end"]) if e.get("end") else None
    out["unless_fn"] = compile_cond(e.get("unless")) if e.get("unless") else None
    return out


def load_params(path: Path) -> dict[str, Param]:
    raw = yaml.safe_load(path.read_text())
    out = {}
    for name, d in raw.items():
        out[name] = Param(name=name, dist=Dist.parse(d["dist"]), origin=d["origin"],
                          description=d.get("description", ""), unit=d.get("unit", ""), notes=d.get("notes", ""),
                          sources=d.get("sources", []) or [], evidence_grade=d.get("evidence_grade"))
    return out


def load_model(actions_path: Path, params: dict[str, Param], extra_actions: list[dict] | None = None) -> Model:
    cat = yaml.safe_load(actions_path.read_text())
    start = datetime.combine(date.fromisoformat(cat["start_date"]), datetime.min.time(), IST)
    acts: list[Action] = []
    for raw in cat["actions"] + list(extra_actions or []):
        acts.extend(build_action(raw, start))
    ids = [a.id for a in acts]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate action ids: {dup}")
    m = Model(start=start, horizon_weeks=int(cat.get("horizon_weeks", 52)),
              graduation_week=to_week(start, cat.get("graduation", "2027-06-30")), actions=acts, params=params,
              offer_classes=cat.get("offer_classes", {}), initial_tokens=cat.get("initial_tokens", {}),
              exogenous=[compile_exogenous(e, start) for e in cat.get("exogenous", [])])
    validate_model(m)
    return m


def validate_model(m: Model) -> None:
    """Fail loudly on references to undefined parameters or offer classes."""
    missing = set()

    def chk(v):
        if isinstance(v, str):
            try:
                float(v)
            except ValueError:
                if v not in m.params:
                    missing.add(v)

    for a in m.actions:
        for s in a.stages:
            if not isinstance(s.delay, (dict, int, float)):
                chk(s.delay)
            elif isinstance(s.delay, dict) and "dist" not in s.delay:
                raise ValueError(f"{a.id}: bad delay {s.delay}")
            for o in s.outcomes:
                if o.p:
                    if not isinstance(o.p.base, dict):
                        chk(o.p.base)
                    for sh in o.p.shifts:
                        chk(sh["param"])
                    for v in o.p.factors.values():
                        chk(v)
                for k, v in o.metrics.items():
                    if k != "offer" and k not in SUM_METRICS + MAX_METRICS:
                        raise ValueError(f"{a.id}: outcome writes unknown or derived metric {k!r}")
                    if k == "offer":
                        if v not in m.offer_classes:
                            raise ValueError(f"{a.id}: unknown offer class {v}")
                    else:
                        chk(v)
        for k in (a.effects.get("metrics") or {}):
            if k not in SUM_METRICS + MAX_METRICS:
                raise ValueError(f"{a.id}: effect writes unknown or derived metric {k!r}")
        for r in a.reveals:
            chk(r)
    for k, v in m.initial_tokens.items():
        if isinstance(v, dict):
            chk(v["param"])
    for e in m.exogenous:
        if isinstance(e.get("hazard"), str):
            chk(e["hazard"])
    for c in m.offer_classes.values():
        if c.get("comp"):
            chk(c["comp"])
    if missing:
        raise ValueError(f"undefined parameters referenced: {sorted(missing)}")
