"""Out-of-sample validation harness for the proxy method.

The first question any model-validation function asks is: *what is the tracking
error of the proxy against realised returns?* This module answers it with a
leave-one-out backtest:

  1. Take a hold-out sample of traded assets and **treat each as if it were a
     private holding** (its fundamentals only).
  2. Build a proxy for it from the **rest** of the universe (the held-out asset
     is excluded - a genuine out-of-sample test).
  3. Compare the proxy basket's realised return series to the asset's own,
     out of sample: **tracking error**, correlation, R² and beta.
  4. Aggregate across the sample.

Return series in this prototype are **illustrative / simulated** - a transparent
factor model (market + sector + single-name idiosyncratic), so the harness and
its statistics can be demonstrated end to end. In production the same backtest
runs on the client's **real** return history; nothing about the method changes,
only the data source. The construction is deliberately such that the systematic
(market/sector) part is capturable by comparables while the single-name
idiosyncratic part is not - which is exactly what the methodology claims a proxy
does and does not represent.

Pure functions; deterministic given the config seed; standard library only.
"""
from __future__ import annotations

import math
import zlib
from random import Random
from statistics import fmean, pstdev
from typing import Any

from engine.mapping.metric_space import build_standardizer, extract_metrics
from engine.mapping.proxy_builder import construct_proxy
from engine.models.baseline_asset import BaselineAsset
from engine.models.private_holding import PrivateHolding

_ANNUALISE = math.sqrt(12.0)  # monthly → annual for vol / tracking error


def _seed(base: int, token: str) -> int:
    """Stable per-token seed (crc32 - deterministic across processes)."""
    return (base ^ zlib.crc32(token.encode("utf-8"))) & 0xFFFFFFFF


def _betas(baseline: list[BaselineAsset]) -> dict[str, float]:
    """Assign each asset a market beta from size / margin / leverage.

    Smaller, lower-margin, more-levered names get a higher market beta - a
    plausible cross-section. Uses the same standardiser as the engine so the
    factor structure is related to (not identical to) the matching metrics.
    """
    std = build_standardizer(
        baseline,
        ["market_value", "ebitda_margin", "leverage"],
        ["market_value"],
    )
    betas: dict[str, float] = {}
    for a in baseline:
        z = std.transform(extract_metrics(a))
        size_z = z.get("market_value", 0.0)
        margin_z = z.get("ebitda_margin", 0.0)
        lev_z = z.get("leverage", 0.0)
        beta = 1.0 - 0.28 * size_z - 0.15 * margin_z + 0.18 * lev_z
        betas[a.id] = max(0.45, min(1.9, beta))
    return betas


def generate_returns(baseline: list[BaselineAsset], cfg: dict[str, Any]) -> dict[str, list[float]]:
    """Deterministic monthly return series per asset (illustrative factor model)."""
    periods = int(cfg.get("periods", 60))
    seed = int(cfg.get("seed", 20260821))
    drift = float(cfg.get("market_drift", 0.006))
    mkt_vol = float(cfg.get("market_vol", 0.045))
    sec_vol = float(cfg.get("sector_vol", 0.030))
    idio_vol = float(cfg.get("idiosyncratic_vol", 0.045))

    market_rng = Random(_seed(seed, "market"))
    market = [market_rng.gauss(drift, mkt_vol) for _ in range(periods)]

    sectors = sorted({a.sector or "-" for a in baseline})
    sector_series: dict[str, list[float]] = {}
    for sector in sectors:
        rng = Random(_seed(seed, f"sector::{sector}"))
        sector_series[sector] = [rng.gauss(0.0, sec_vol) for _ in range(periods)]

    betas = _betas(baseline)
    returns: dict[str, list[float]] = {}
    for a in baseline:
        rng = Random(_seed(seed, f"asset::{a.id}"))
        b = betas[a.id]
        sec = sector_series[a.sector or "-"]
        returns[a.id] = [
            b * market[t] + sec[t] + rng.gauss(0.0, idio_vol)
            for t in range(periods)
        ]
    return returns


# --------------------------------------------------------------------------- #
# statistics helpers
# --------------------------------------------------------------------------- #
def _corr(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = fmean(xs), fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(sxx * syy)
    return sxy / denom if denom else 0.0


def _beta(actual: list[float], proxy: list[float]) -> float:
    mp = fmean(proxy)
    var = sum((p - mp) ** 2 for p in proxy)
    if not var:
        return 0.0
    ma = fmean(actual)
    cov = sum((a - ma) * (p - mp) for a, p in zip(actual, proxy))
    return cov / var


def _holding_from_asset(a: BaselineAsset) -> PrivateHolding:
    """Treat a traded asset as a private holding described by its fundamentals."""
    from engine.models.asset_class import AssetClassType

    return PrivateHolding(
        holding_id=a.id, name=a.name,
        asset_class=AssetClassType.DIRECT_PRIVATE_EQUITY,
        currency=a.currency, region=a.region, sector=a.sector,
        revenue=a.revenue, ebitda=a.ebitda, net_income=a.net_income,
        net_debt=a.net_debt, last_nav=a.market_cap, source="backtest",
    )


def _select_test_set(baseline: list[BaselineAsset], count: int) -> list[BaselineAsset]:
    """Central slice by size - a representative mid-cap hold-out sample."""
    ranked = sorted((a for a in baseline if a.market_cap), key=lambda a: a.market_cap or 0.0)
    count = min(count, len(ranked))
    start = max(0, (len(ranked) - count) // 2)
    return ranked[start:start + count]


def run_backtest(
    baseline: list[BaselineAsset],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Leave-one-out out-of-sample tracking-error backtest. See module docstring."""
    bt_cfg = config.get("backtest", {}) or {}
    returns = generate_returns(baseline, bt_cfg)
    test_set = _select_test_set(baseline, int(bt_cfg.get("test_count", 20)))

    results: list[dict[str, Any]] = []
    for target in test_set:
        others = [a for a in baseline if a.id != target.id]
        proxy = construct_proxy(_holding_from_asset(target), others, config)
        if proxy.status != "constructed" or not proxy.comparables:
            continue

        actual = returns[target.id]
        periods = len(actual)
        proxy_series = [0.0] * periods
        for comp in proxy.comparables:
            series = returns.get(comp.asset_id)
            if not series:
                continue
            for t in range(periods):
                proxy_series[t] += comp.weight * series[t]

        diff = [a - p for a, p in zip(actual, proxy_series)]
        te = pstdev(diff) * _ANNUALISE
        corr = _corr(actual, proxy_series)
        results.append({
            "asset_id": target.id,
            "name": target.name,
            "ticker": target.ticker,
            "sector": target.sector,
            "n_comparables": len(proxy.comparables),
            "confidence": proxy.confidence,
            "tracking_error": round(te, 4),
            "correlation": round(corr, 4),
            "r2": round(corr * corr, 4),
            "beta": round(_beta(actual, proxy_series), 4),
            "vol_actual": round(pstdev(actual) * _ANNUALISE, 4),
            "vol_proxy": round(pstdev(proxy_series) * _ANNUALISE, 4),
        })

    return {
        "config_version": str(config.get("version", "unknown")),
        "periods": int(bt_cfg.get("periods", 60)),
        "n_tested": len(results),
        "returns_basis": "simulated",  # prototype: illustrative factor-model returns
        "aggregate": _aggregate(results),
        "results": results,
        "note": (
            "Out-of-sample leave-one-out backtest. Return series are illustrative "
            "(a market + sector + idiosyncratic factor model) so the harness can be "
            "demonstrated; in production it runs on the client's real return history. "
            "Tracking error is dominated by single-name idiosyncratic risk, which a "
            "proxy cannot capture - the proxy represents systematic/market behaviour, "
            "which the correlation and beta columns measure."
        ),
    }


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}

    def _median(key: str) -> float:
        vals = sorted(r[key] for r in results)
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0

    return {
        "median_tracking_error": round(_median("tracking_error"), 4),
        "mean_tracking_error": round(fmean(r["tracking_error"] for r in results), 4),
        "median_correlation": round(_median("correlation"), 4),
        "mean_correlation": round(fmean(r["correlation"] for r in results), 4),
        "median_r2": round(_median("r2"), 4),
        "mean_beta": round(fmean(r["beta"] for r in results), 4),
    }
