"""Parameter distributions and keyed random streams.

Every random quantity is drawn from a stream keyed by (seed, purpose, name), so two
strategies evaluated with the same seed see the same parameter values and the same
outcome uniforms for the same action. That is common random numbers: differences
between strategies are not swamped by sampling noise, and runs are reproducible.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import numpy as np

ORIGINS = (
    "observed_base_rate", "published_empirical", "official_statistic", "organizer_published",
    "historical_user", "calibrated", "expert_judgment", "scenario_assumption",
    "illustrative_placeholder", "unknown",
)

_DIST_RE = re.compile(r"^\s*(\w+)\s*\(([^)]*)\)\s*$")


def stream(seed: int, *key: str) -> np.random.Generator:
    """Independent generator for a named purpose, stable across processes."""
    h = hashlib.sha256(("|".join(str(k) for k in key)).encode()).digest()
    words = [int.from_bytes(h[i:i + 4], "little") for i in range(0, 16, 4)]
    return np.random.default_rng(np.random.SeedSequence([seed, *words]))


@dataclass
class Dist:
    kind: str
    args: tuple[float, ...]

    @classmethod
    def parse(cls, s: str) -> "Dist":
        m = _DIST_RE.match(s)
        if not m:
            raise ValueError(f"bad distribution: {s!r}")
        kind = m.group(1).lower()
        args = tuple(float(x) for x in m.group(2).split(",") if x.strip())
        need = {"beta": 2, "normal": 2, "lognormal": 2, "triangular": 3, "fixed": 1, "bernoulli": 1, "uniform": 2}
        if kind not in need or len(args) != need[kind]:
            raise ValueError(f"bad distribution: {s!r}")
        if kind == "triangular" and not (args[0] <= args[1] <= args[2]):
            raise ValueError(f"triangular needs low <= mode <= high: {s!r}")
        return cls(kind, args)

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        a = self.args
        k = self.kind
        if k == "beta":
            return rng.beta(a[0], a[1], n)
        if k == "normal":
            return rng.normal(a[0], a[1], n)
        if k == "lognormal":  # (median, geometric sd)
            return a[0] * np.exp(rng.normal(0.0, np.log(a[1]), n))
        if k == "triangular":
            if a[0] == a[2]:
                return np.full(n, a[0])
            return rng.triangular(a[0], a[1], a[2], n)
        if k == "fixed":
            return np.full(n, a[0])
        if k == "bernoulli":
            return (rng.random(n) < a[0]).astype(float)
        if k == "uniform":
            return rng.uniform(a[0], a[1], n)
        raise AssertionError(k)

    def quantile(self, q: float) -> float:
        """Approximate quantile, used for one-at-a-time sensitivity."""
        from scipy import stats
        a = self.args
        k = self.kind
        if k == "beta":
            return float(stats.beta.ppf(q, a[0], a[1]))
        if k == "normal":
            return float(stats.norm.ppf(q, a[0], a[1]))
        if k == "lognormal":
            return float(a[0] * np.exp(stats.norm.ppf(q) * np.log(a[1])))
        if k == "triangular":
            lo, mo, hi = a
            if hi == lo:
                return lo
            c = (mo - lo) / (hi - lo)
            return float(stats.triang.ppf(q, c, loc=lo, scale=hi - lo))
        if k == "fixed":
            return a[0]
        if k == "bernoulli":
            return 1.0 if q > 1 - a[0] else 0.0
        if k == "uniform":
            return a[0] + q * (a[1] - a[0])
        raise AssertionError(k)

    def mean(self) -> float:
        a = self.args
        return {
            "beta": lambda: a[0] / (a[0] + a[1]),
            "normal": lambda: a[0],
            "lognormal": lambda: a[0] * np.exp(0.5 * np.log(a[1]) ** 2),
            "triangular": lambda: sum(a) / 3,
            "fixed": lambda: a[0],
            "bernoulli": lambda: a[0],
            "uniform": lambda: (a[0] + a[1]) / 2,
        }[self.kind]()

    def __str__(self) -> str:
        return f"{self.kind}({', '.join(f'{x:g}' for x in self.args)})"


@dataclass
class Param:
    name: str
    dist: Dist
    origin: str
    description: str = ""
    unit: str = ""
    notes: str = ""
    sources: list = field(default_factory=list)
    evidence_grade: str | None = None

    def __post_init__(self):
        if self.origin not in ORIGINS:
            raise ValueError(f"{self.name}: unknown origin {self.origin!r}")


class ParamSet:
    """Holds parameter definitions and per-world draws for one simulation run."""

    def __init__(self, params: dict[str, Param], seed: int, n: int, overrides: dict[str, float] | None = None):
        self.defs = params
        self.seed = seed
        self.n = n
        self.overrides = dict(overrides or {})
        self._draws: dict[str, np.ndarray] = {}

    def __getitem__(self, name: str) -> np.ndarray:
        if name not in self._draws:
            if name in self.overrides:
                self._draws[name] = np.full(self.n, float(self.overrides[name]))
            else:
                p = self.defs.get(name)
                if p is None:
                    raise KeyError(f"unknown parameter {name!r}")
                self._draws[name] = p.dist.sample(stream(self.seed, "param", name), self.n)
        return self._draws[name]

    def value_or_param(self, v) -> np.ndarray:
        if isinstance(v, (int, float)):
            return np.full(self.n, float(v))
        if isinstance(v, str):
            try:
                return np.full(self.n, float(v))
            except ValueError:
                return self[v]
        if isinstance(v, dict) and "dist" in v:
            key = "inline:" + v["dist"]
            if key not in self._draws:
                self._draws[key] = Dist.parse(v["dist"]).sample(stream(self.seed, "param", key), self.n)
            return self._draws[key]
        raise ValueError(f"cannot resolve value {v!r}")

    @property
    def drawn(self) -> dict[str, np.ndarray]:
        return self._draws
