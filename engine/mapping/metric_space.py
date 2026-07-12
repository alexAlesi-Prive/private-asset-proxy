"""Shared metric space: turn any asset (private or traded) into comparable coordinates.

The engine compares holdings to traded assets purely on their fundamental
metrics (Privé's approach — no fixed factor library). This module extracts those
metrics, log-scales size variables, z-scores everything against the baseline
universe, and measures distance. Pure functions; no I/O.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


def extract_metrics(obj: Any) -> dict[str, float]:
    """Return the numeric comparison metrics available on an asset-like object.

    Works for both :class:`PrivateHolding` and :class:`BaselineAsset` via
    attribute lookup. Derived margins are computed when their parts exist.
    ``market_value`` unifies a traded asset's market cap and a private holding's
    last NAV as a size anchor.
    """
    def g(name: str) -> float | None:
        v = getattr(obj, name, None)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    rev, ebitda, ni = g("revenue"), g("ebitda"), g("net_income")
    mv = g("market_cap")
    if mv is None:
        mv = g("last_nav")
    ey = g("expected_yield")

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
    if rev not in (None, 0) and ebitda is not None:
        m["ebitda_margin"] = ebitda / rev
    if rev not in (None, 0) and ni is not None:
        m["net_margin"] = ni / rev
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
    """Euclidean distance over the standardised metrics present in both points."""
    total, n = 0.0, 0
    for metric in metrics:
        if metric in a_std and metric in b_std:
            total += (a_std[metric] - b_std[metric]) ** 2
            n += 1
    return math.sqrt(total) if n else float("inf")
