"""Construct a proxy for a private holding from its nearest traded comparables.

This is the deterministic, config-driven core of Privé's method: place the
holding in the shared metric space and build a weighted basket of the closest
traded assets, with a full explanation for audit. Pure function - inject the
holding, the baseline universe, and the config.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import mean as _mean
from typing import Any

from engine.mapping.capital_calls import summarize_capital_calls
from engine.mapping.leverage import summarize_leverage
from engine.mapping.metric_space import (
    DistanceModel,
    build_standardizer,
    extract_metrics,
)
from engine.models.baseline_asset import BaselineAsset
from engine.models.private_holding import PrivateHolding


@dataclass
class Comparable:
    asset_id: str
    name: str
    ticker: str | None
    sector: str | None
    region: str | None
    currency: str | None
    distance: float
    weight: float  # 0..1, basket weights sum to 1
    metrics: dict[str, float]


@dataclass
class ProxyResult:
    holding_id: str
    holding_name: str
    asset_class: str | None
    status: str  # "constructed" | "insufficient_data" | "no_comparables"
    reason: str | None
    metrics_used: list[str]
    filters_applied: dict[str, Any]
    filters_relaxed: bool
    comparables: list[Comparable]
    proxy_point: dict[str, float]
    holding_metrics: dict[str, float]
    confidence: str | None
    coverage: float
    config_version: str
    generated_at: str
    distance_metric: str = "mahalanobis"
    capital_call: dict[str, Any] | None = None
    capital_structure: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def construct_proxy(
    holding: PrivateHolding,
    baseline: list[BaselineAsset],
    config: dict[str, Any],
) -> ProxyResult:
    """Build a proxy basket for ``holding`` from ``baseline`` per ``config``."""
    cfg = config.get("construction", {})
    metrics_cfg = list(cfg.get("metrics", []))
    log_scaled = cfg.get("log_scaled_metrics", [])
    method = str(cfg.get("distance", "mahalanobis"))
    version = str(config.get("version", "unknown"))
    now = datetime.now(timezone.utc).isoformat()

    holding_metrics = extract_metrics(holding)
    metrics_used = [m for m in metrics_cfg if m in holding_metrics]

    common = dict(
        holding_id=holding.holding_id,
        holding_name=holding.name,
        asset_class=holding.asset_class.value if holding.asset_class else None,
        metrics_used=metrics_used,
        holding_metrics=holding_metrics,
        config_version=version,
        generated_at=now,
        distance_metric=method,
        capital_call=summarize_capital_calls(holding),
    )

    if not metrics_used:
        return ProxyResult(
            status="insufficient_data",
            reason="No usable numeric metric supplied; cannot place the holding in metric space.",
            filters_applied={}, filters_relaxed=False, comparables=[],
            proxy_point={}, confidence=None, coverage=0.0, **common,
        )

    # --- eligibility & filters ---
    def has_all_used(a: BaselineAsset) -> bool:
        am = extract_metrics(a)
        return all(m in am for m in metrics_used)

    eligible_all = [a for a in baseline if has_all_used(a)]
    eligible = eligible_all
    filters = cfg.get("filters", {}) or {}
    applied: dict[str, Any] = {}
    if filters.get("same_sector") and holding.sector:
        applied["same_sector"] = holding.sector
        eligible = [a for a in eligible if (a.sector or "").lower() == holding.sector.lower()]
    if filters.get("same_region") and holding.region:
        applied["same_region"] = holding.region
        eligible = [a for a in eligible if (a.region or "").lower() == holding.region.lower()]

    relaxed = False
    relax_threshold = int(filters.get("relax_if_fewer_than", 0) or 0)
    if len(eligible) < relax_threshold:
        eligible, relaxed = eligible_all, True

    coverage = round(len(metrics_used) / len(metrics_cfg), 4) if metrics_cfg else 0.0
    min_comp = int(cfg.get("min_comparables", 1))
    if len(eligible) < max(min_comp, 1):
        return ProxyResult(
            status="no_comparables",
            reason=f"Only {len(eligible)} eligible comparable(s) (minimum {min_comp}).",
            filters_applied=applied, filters_relaxed=relaxed, comparables=[],
            proxy_point={}, confidence="low", coverage=coverage, **common,
        )

    # --- standardise (fit on the full universe for stable stats) & score ---
    # Mahalanobis divides out the correlation between size metrics; per-metric
    # weights keep margins from carrying the same weight as size. Distances are
    # RMS-normalised so they are comparable across holdings with different
    # metric coverage (see metric_space).
    standardizer = build_standardizer(baseline, metrics_cfg, log_scaled)
    model = DistanceModel(
        standardizer=standardizer,
        method=method,
        weights={str(k): float(v) for k, v in (cfg.get("metric_weights") or {}).items()},
        ridge=float(cfg.get("mahalanobis_ridge", 0.15)),
    ).fit(baseline)

    h_std = standardizer.transform({m: holding_metrics[m] for m in metrics_used})
    scored = sorted(
        ((model.distance(h_std, standardizer.transform(extract_metrics(a)), metrics_used), a)
         for a in eligible),
        key=lambda t: t[0],
    )
    chosen = scored[: min(int(cfg.get("k_comparables", 8)), len(scored))]

    # --- weights (basket sums to 1, with a distance floor + single-name cap) ---
    weights = _weights([d for d, _ in chosen], cfg)
    comparables = [
        Comparable(
            asset_id=a.id, name=a.name, ticker=a.ticker, sector=a.sector,
            region=a.region, currency=a.currency, distance=round(d, 4),
            weight=round(w, 6), metrics=extract_metrics(a),
        )
        for (d, a), w in zip(chosen, weights)
    ]

    # --- implied proxy point (weighted average of comparables' raw metrics) ---
    axes = config.get("scatter", {}).get("available_axes", metrics_cfg)
    proxy_point: dict[str, float] = {}
    for metric in axes:
        num = wsum = 0.0
        for comp, w in zip(comparables, weights):
            if metric in comp.metrics:
                num += w * comp.metrics[metric]
                wsum += w
        if wsum > 0:
            proxy_point[metric] = num / wsum

    confidence = _confidence(
        metric_count=len(metrics_used),
        mean_distance=_mean([d for d, _ in chosen]),
        relaxed=relaxed,
        conf_cfg=config.get("confidence", {}) or {},
    )

    tax_rate = float((config.get("leverage", {}) or {}).get("marginal_tax_rate", 0.25))
    capital_structure = summarize_leverage(holding, comparables, tax_rate)

    return ProxyResult(
        status="constructed", reason=None, filters_applied=applied,
        filters_relaxed=relaxed, comparables=comparables, proxy_point=proxy_point,
        confidence=confidence, coverage=coverage,
        capital_structure=capital_structure, **common,
    )


def _weights(distances: list[float], cfg: dict[str, Any]) -> list[float]:
    """Distances → basket weights, with two stability guards.

    * ``distance_floor`` - inverse-distance weighting degenerates when a
      comparable sits at ~zero distance (it would take ~100% of the basket).
      Flooring the distance keeps the basket diversified.
    * ``max_weight`` - hard cap on any single comparable, water-filled onto the
      rest, so k≥3 names actually share the basket.
    """
    eps = 1e-9
    floor = float(cfg.get("distance_floor", 0.0) or 0.0)
    d_adj = [max(d, floor) for d in distances]
    if cfg.get("weighting") == "softmax":
        temp = float(cfg.get("softmax_temperature", 1.0)) or 1.0
        raw = [math.exp(-d / temp) for d in d_adj]
    else:  # inverse_distance (default)
        raw = [1.0 / (d + eps) for d in d_adj]
    total = sum(raw) or 1.0
    weights = [r / total for r in raw]

    cap = float(cfg.get("max_weight", 1.0) or 1.0)
    if 0.0 < cap < 1.0:
        weights = _apply_cap(weights, cap)
    return weights


def _apply_cap(weights: list[float], cap: float) -> list[float]:
    """Cap each weight at ``cap`` and redistribute the excess (water-filling)."""
    n = len(weights)
    if n == 0:
        return weights
    if cap * n <= 1.0:  # cap infeasible for this many names -> equal weights
        return [1.0 / n] * n
    w = list(weights)
    for _ in range(n):
        over = [i for i, x in enumerate(w) if x > cap + 1e-12]
        if not over:
            break
        excess = sum(w[i] - cap for i in over)
        for i in over:
            w[i] = cap
        under = [i for i in range(n) if i not in over]
        pool = sum(w[i] for i in under)
        if pool <= 0:
            break
        for i in under:
            w[i] += excess * (w[i] / pool)
    return w


def _confidence(metric_count: int, mean_distance: float, relaxed: bool, conf_cfg: dict) -> str:
    if metric_count < int(conf_cfg.get("medium_metric_count", 2)) or \
            mean_distance >= float(conf_cfg.get("far_distance", math.inf)):
        return "low"
    if metric_count >= int(conf_cfg.get("high_metric_count", 10**9)) and \
            mean_distance <= float(conf_cfg.get("near_distance", 0.0)) and not relaxed:
        return "high"
    return "medium"
