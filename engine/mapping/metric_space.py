"""Shared metric space: turn any asset (private or traded) into comparable coordinates.

The engine compares holdings to traded assets purely on their fundamental
metrics (Privé's approach — no fixed factor library). This module extracts those
metrics, log-scales size variables, z-scores everything against the baseline
universe, and measures distance. Pure functions; no I/O.

Two refinements the naive "Euclidean distance on z-scores" recipe needs, both
requested by model-validation review:

* **Correlation between metrics.** Revenue, EBITDA and net income move together,
  so plain Euclidean distance double-counts *size*. The :class:`DistanceModel`
  offers a **Mahalanobis** distance that divides out that shared covariance
  (estimated from the baseline universe, ridge-regularised toward the identity).
* **Cross-coverage comparability.** A holding with two metrics and one with five
  should not live on different distance scales. Distances are therefore
  **root-mean-square** over the metrics actually used (divided by the dimension
  count), so a "distance of 1" means the same thing regardless of coverage.

Per-metric weights let the config say, e.g., that EBITDA margin should not carry
the same weight as size in determining return behaviour.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


def extract_metrics(obj: Any) -> dict[str, float]:
    """Return the numeric comparison metrics available on an asset-like object.

    Works for both :class:`PrivateHolding` and :class:`BaselineAsset` via
    attribute lookup. Derived metrics are computed when their parts exist.
    ``market_value`` unifies a traded asset's market cap and a private holding's
    last NAV as a size anchor. ``leverage`` (net debt / EBITDA) captures capital
    structure — supplied directly, else derived from ``net_debt`` and EBITDA.
    """
    def g(name: str) -> float | None:
        v = getattr(obj, name, None)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    rev, ebitda, ni = g("revenue"), g("ebitda"), g("net_income")
    mv = g("market_cap")
    if mv is None:
        mv = g("last_nav")
    ey = g("expected_yield")
    net_debt = g("net_debt")
    leverage = g("leverage")  # a directly supplied net-debt/EBITDA multiple

    m: dict[str, float] = {}
    if rev is not None:
        m["revenue"] = rev
    if ebitda is not None:
        m["ebitda"] = ebitda
    if ni is not None:
        m["net_income"] = ni
    if mv is not None:
        m["market_value"] = mv
    if ey is not None:
        m["expected_yield"] = ey
    if net_debt is not None:
        m["net_debt"] = net_debt
    if rev not in (None, 0) and ebitda is not None:
        m["ebitda_margin"] = ebitda / rev
    if rev not in (None, 0) and ni is not None:
        m["net_margin"] = ni / rev
    # Leverage (net debt / EBITDA): explicit multiple wins, else derive it — but
    # only for positive EBITDA, where the multiple is meaningful.
    if leverage is not None:
        m["leverage"] = leverage
    elif net_debt is not None and ebitda is not None and ebitda > 0:
        m["leverage"] = net_debt / ebitda
    return m


def _slog(x: float) -> float:
    """Signed log1p — compresses order-of-magnitude size metrics, keeps sign."""
    return math.copysign(math.log1p(abs(x)), x)


@dataclass
class Standardizer:
    """z-score transform fitted on the baseline universe (per metric)."""

    params: dict[str, tuple[float, float]]  # metric -> (mean, std) in transformed space
    log_scaled: frozenset[str]

    def _pre(self, metric: str, value: float) -> float:
        return _slog(value) if metric in self.log_scaled else value

    def transform(self, metrics: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        for metric, value in metrics.items():
            if metric in self.params:
                mean, std = self.params[metric]
                out[metric] = (self._pre(metric, value) - mean) / std
        return out


def build_standardizer(
    assets: Iterable[Any], metrics: Iterable[str], log_scaled: Iterable[str]
) -> Standardizer:
    """Fit per-metric mean/σ across the baseline universe (population σ)."""
    log_scaled = frozenset(log_scaled)
    asset_metrics = [extract_metrics(a) for a in assets]
    params: dict[str, tuple[float, float]] = {}
    for metric in metrics:
        values = [
            (_slog(am[metric]) if metric in log_scaled else am[metric])
            for am in asset_metrics
            if metric in am
        ]
        if values:
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / len(values)
            params[metric] = (mean, math.sqrt(var) or 1.0)
    return Standardizer(params=params, log_scaled=log_scaled)


def distance(a_std: dict[str, float], b_std: dict[str, float], metrics: Iterable[str]) -> float:
    """Root-mean-square Euclidean distance over the standardised shared metrics.

    Dividing by the number of contributing dimensions keeps distances comparable
    across holdings with different metric coverage. Retained as a free function
    for the simple/euclidean path and for tests.
    """
    total, n = 0.0, 0
    for metric in metrics:
        if metric in a_std and metric in b_std:
            total += (a_std[metric] - b_std[metric]) ** 2
            n += 1
    return math.sqrt(total / n) if n else float("inf")


# --------------------------------------------------------------------------- #
# Mahalanobis-capable distance model
# --------------------------------------------------------------------------- #
def _matrix_inverse(mat: list[list[float]]) -> list[list[float]]:
    """Invert a small square matrix via Gauss-Jordan (metric counts are tiny)."""
    n = len(mat)
    aug = [list(row) + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(mat)]
    for col in range(n):
        # Partial pivot for stability.
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            aug[pivot][col] += 1e-9  # nudge a singular pivot
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        aug[col] = [v / piv for v in aug[col]]
        for r in range(n):
            if r != col and aug[r][col] != 0.0:
                factor = aug[r][col]
                aug[r] = [v - factor * aug[col][k] for k, v in enumerate(aug[r])]
    return [row[n:] for row in aug]


@dataclass
class DistanceModel:
    """Distance between a holding and a comparable in standardised metric space.

    ``method`` is ``"mahalanobis"`` (default — divides out inter-metric
    correlation) or ``"euclidean"``. ``weights`` re-emphasise metrics (applied as
    ``√w`` scaling of each standardised axis, so weighting is consistent between
    the two methods and the covariance used by Mahalanobis). ``ridge`` shrinks
    the covariance toward the identity (robust/regularised Mahalanobis; a large
    ridge → Euclidean). Distances are RMS-normalised by the dimension count.
    """

    standardizer: Standardizer
    method: str = "mahalanobis"
    weights: dict[str, float] = field(default_factory=dict)
    ridge: float = 0.15
    _cov: dict[tuple[str, str], float] = field(default_factory=dict)
    _precision_cache: dict[tuple[str, ...], list[list[float]]] = field(default_factory=dict)

    # -- coordinate helpers -------------------------------------------------- #
    def _w(self, metric: str) -> float:
        return float(self.weights.get(metric, 1.0))

    def _scaled(self, std: dict[str, float]) -> dict[str, float]:
        """Apply √weight to each standardised coordinate."""
        return {m: v * math.sqrt(self._w(m)) for m, v in std.items()}

    # -- fitting ------------------------------------------------------------- #
    def fit(self, assets: Sequence[Any]) -> "DistanceModel":
        """Estimate the (weighted, standardised) metric covariance from a universe."""
        if self.method != "mahalanobis":
            return self
        scaled = [self._scaled(self.standardizer.transform(extract_metrics(a))) for a in assets]
        metrics = list(self.standardizer.params.keys())
        cov: dict[tuple[str, str], float] = {}
        for i, mj in enumerate(metrics):
            for mk in metrics[i:]:
                pairs = [(v[mj], v[mk]) for v in scaled if mj in v and mk in v]
                # Standardised coords are ~zero-mean, so E[zj·zk] ≈ cov(j,k).
                c = sum(a * b for a, b in pairs) / len(pairs) if pairs else 0.0
                cov[(mj, mk)] = cov[(mk, mj)] = c
        self._cov = cov
        self._precision_cache = {}
        return self

    def _precision(self, metrics: tuple[str, ...]) -> list[list[float]]:
        cached = self._precision_cache.get(metrics)
        if cached is not None:
            return cached
        n = len(metrics)
        # Ridge-regularised covariance submatrix (shrink toward the identity).
        cov = [
            [self._cov.get((a, b), 1.0 if a == b else 0.0) + (self.ridge if a == b else 0.0)
             for b in metrics]
            for a in metrics
        ]
        precision = _matrix_inverse(cov) if n else []
        self._precision_cache[metrics] = precision
        return precision

    # -- distance ------------------------------------------------------------ #
    def distance(self, a_std: dict[str, float], b_std: dict[str, float],
                 metrics: Sequence[str]) -> float:
        shared = [m for m in metrics if m in a_std and m in b_std]
        if not shared:
            return float("inf")
        a_s, b_s = self._scaled(a_std), self._scaled(b_std)
        delta = [a_s[m] - b_s[m] for m in shared]
        if self.method == "mahalanobis" and self._cov:
            precision = self._precision(tuple(shared))
            q = 0.0
            for i in range(len(shared)):
                for j in range(len(shared)):
                    q += delta[i] * precision[i][j] * delta[j]
            q = max(q, 0.0)  # numerical guard; a valid Mahalanobis form is ≥ 0
        else:
            q = sum(d * d for d in delta)
        return math.sqrt(q / len(shared))
