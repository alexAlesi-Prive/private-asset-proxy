"""Tests for metric-based proxy construction.

Run standalone: python3 -m engine.tests.test_proxy_builder
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from engine.mapping.backtest import run_backtest
from engine.mapping.config import load_mapping_config
from engine.mapping.proxy_builder import construct_proxy
from engine.mapping.universe import load_baseline_universe
from engine.models.asset_class import AssetClassType, classify
from engine.models.private_holding import PrivateHolding

CONFIG = load_mapping_config()
BASELINE = load_baseline_universe()


def _holding(**kw) -> PrivateHolding:
    base = dict(
        holding_id="TEST-1", name="Test Holding",
        asset_class=AssetClassType.DIRECT_PRIVATE_EQUITY, currency="USD",
    )
    base.update(kw)
    return PrivateHolding(**base)


def test_baseline_loaded() -> None:
    assert len(BASELINE) == 50
    assert all(a.revenue and a.ebitda is not None for a in BASELINE)


def test_construct_basic_proxy() -> None:
    h = _holding(sector="Technology", region="US",
                 revenue=20000, ebitda=6000, net_income=3000)
    res = construct_proxy(h, BASELINE, CONFIG)
    assert res.status == "constructed"
    # all five configured metrics available (3 raw + 2 derived margins)
    assert set(res.metrics_used) == {"revenue", "ebitda", "net_income",
                                     "ebitda_margin", "net_margin"}
    assert len(res.comparables) == CONFIG["construction"]["k_comparables"]
    total = sum(c.weight for c in res.comparables)
    assert abs(total - 1.0) < 1e-5                     # basket sums to 100% (6dp rounding)
    assert all(c.weight > 0 for c in res.comparables)
    # distances sorted ascending (nearest first)
    dists = [c.distance for c in res.comparables]
    assert dists == sorted(dists)
    # proxy point populated on the default scatter axes
    assert "revenue" in res.proxy_point and "ebitda" in res.proxy_point
    assert res.confidence in {"high", "medium", "low"}
    assert res.config_version == CONFIG["version"]


def test_determinism() -> None:
    h = _holding(revenue=15000, ebitda=4000, net_income=2000)
    a = construct_proxy(h, BASELINE, CONFIG)
    b = construct_proxy(h, BASELINE, CONFIG)
    assert [(c.asset_id, c.weight) for c in a.comparables] == \
           [(c.asset_id, c.weight) for c in b.comparables]
    assert a.proxy_point == b.proxy_point


def test_single_metric_lowers_confidence() -> None:
    h = _holding(revenue=8000)  # only one metric
    res = construct_proxy(h, BASELINE, CONFIG)
    assert res.status == "constructed"
    assert res.metrics_used == ["revenue"]
    assert res.confidence == "low"
    assert res.coverage < 0.5


def test_insufficient_data() -> None:
    h = _holding()  # no numeric metrics at all
    res = construct_proxy(h, BASELINE, CONFIG)
    assert res.status == "insufficient_data"
    assert res.comparables == []
    assert res.confidence is None


def test_sector_filter_restricts_comparables() -> None:
    cfg = copy.deepcopy(CONFIG)
    cfg["construction"]["filters"]["same_sector"] = True
    cfg["construction"]["filters"]["relax_if_fewer_than"] = 0  # don't relax
    h = _holding(sector="Healthcare", revenue=40000, ebitda=15000, net_income=8000)
    res = construct_proxy(h, BASELINE, cfg)
    assert res.status == "constructed"
    assert res.filters_applied.get("same_sector") == "Healthcare"
    assert all(c.sector == "Healthcare" for c in res.comparables)


def test_capital_call_summary() -> None:
    h = _holding(
        asset_class=AssetClassType.PRIVATE_EQUITY_FUND, sector="Consumer Discretionary",
        revenue=9000, ebitda=2200, net_income=1100, last_nav=15000,
        commitment=50000, paid_in=30000, capital_call_line=5000,
        capital_calls=[
            {"date": "2022-03-01", "amount": 12000, "purpose": "Acq"},
            {"date": "2023-06-15", "amount": 18000, "purpose": "Follow-on"},
        ],
    )
    cc = construct_proxy(h, BASELINE, CONFIG).to_dict()["capital_call"]
    assert cc["commitment"] == 50000 and cc["paid_in"] == 30000
    assert cc["uncalled"] == 20000 and cc["pct_called"] == 0.6
    assert cc["net_uncovered_commitment"] == 15000            # uncalled - line
    assert cc["effective_exposure"] == 15000 and cc["exposure_basis"] == "nav"
    assert cc["calls"][0]["pct_of_commitment"] == 0.24
    # No capital-call inputs -> section omitted entirely.
    plain = _holding(revenue=8000, ebitda=2000)
    assert construct_proxy(plain, BASELINE, CONFIG).to_dict()["capital_call"] is None


def test_paid_in_defaults_to_schedule_sum() -> None:
    h = _holding(
        asset_class=AssetClassType.PRIVATE_EQUITY_FUND, revenue=5000, ebitda=1200,
        commitment=20000,
        capital_calls=[{"date": "2023-01-01", "amount": 8000, "purpose": "x"}],
    )
    cc = construct_proxy(h, BASELINE, CONFIG).to_dict()["capital_call"]
    assert cc["paid_in"] == 8000 and cc["uncalled"] == 12000       # paid-in from schedule
    assert cc["exposure_basis"] == "paid_in"                        # no NAV -> paid-in


def test_leverage_matched_and_relevered() -> None:
    # A 5x-levered buyout: net_debt/EBITDA = 30000/6000 = 5.0.
    h = _holding(sector="Technology", region="US", revenue=20000, ebitda=6000,
                 net_income=1500, net_debt=30000, last_nav=24000)
    res = construct_proxy(h, BASELINE, CONFIG)
    assert "leverage" in res.metrics_used                 # leverage is a matching axis
    assert res.holding_metrics["leverage"] == 5.0
    cs = res.to_dict()["capital_structure"]
    assert cs is not None and cs["holding_leverage"] == 5.0
    assert cs["relever_factor"] > 1.0                     # more levered than comps -> beta up


def test_weight_cap_and_floor() -> None:
    h = _holding(revenue=20000, ebitda=6000, net_income=3000)
    res = construct_proxy(h, BASELINE, CONFIG)
    cap = CONFIG["construction"]["max_weight"]
    assert all(c.weight <= cap + 1e-9 for c in res.comparables)   # no single name dominates
    assert abs(sum(c.weight for c in res.comparables) - 1.0) < 1e-5


def test_distance_is_rms_normalised() -> None:
    # RMS normalisation keeps nearest-comparable distances on a comparable scale
    # whether the holding has one metric or several (not summed-over-dims blow-ups).
    one = construct_proxy(_holding(revenue=20000), BASELINE, CONFIG)
    many = construct_proxy(_holding(revenue=20000, ebitda=6000, net_income=3000), BASELINE, CONFIG)
    assert one.comparables[0].distance < 5.0
    assert many.comparables[0].distance < 5.0


def test_euclidean_and_mahalanobis_both_construct() -> None:
    cfg = copy.deepcopy(CONFIG)
    cfg["construction"]["distance"] = "euclidean"
    h = _holding(revenue=20000, ebitda=6000, net_income=3000)
    eucl = construct_proxy(h, BASELINE, cfg)
    maha = construct_proxy(h, BASELINE, CONFIG)
    assert eucl.status == "constructed" and eucl.distance_metric == "euclidean"
    assert maha.status == "constructed" and maha.distance_metric == "mahalanobis"


def test_hedge_fund_is_unsupported() -> None:
    # Hedge funds are deliberately routed to manual mapping (return-based style
    # analysis is the right tool, not revenue/EBITDA comparables).
    for spelling in ("Hedge Fund", "HedgeFund", "HEDGE_FUND", "hf"):
        assert classify(spelling) is None


def test_deployment_stage_from_vintage() -> None:
    h = _holding(asset_class=AssetClassType.PRIVATE_EQUITY_FUND, revenue=9000, ebitda=2200,
                 commitment=50000, paid_in=10000, vintage_year=2024)
    dep = construct_proxy(h, BASELINE, CONFIG).to_dict()["capital_call"]["deployment"]
    assert dep["j_curve_stage"] == "investing"            # 20% called -> early J-curve
    assert dep["fund_age_years"] == datetime.now(timezone.utc).year - 2024


def test_backtest_runs_and_is_deterministic() -> None:
    a = run_backtest(BASELINE, CONFIG)
    b = run_backtest(BASELINE, CONFIG)
    assert a["n_tested"] > 0
    agg = a["aggregate"]
    assert agg["median_tracking_error"] > 0               # realised, non-trivial TE
    assert 0.0 <= agg["median_correlation"] <= 1.0
    assert a["results"] == b["results"]                   # deterministic given the seed


ALL_TESTS = [
    test_baseline_loaded,
    test_construct_basic_proxy,
    test_determinism,
    test_single_metric_lowers_confidence,
    test_insufficient_data,
    test_sector_filter_restricts_comparables,
    test_capital_call_summary,
    test_paid_in_defaults_to_schedule_sum,
    test_leverage_matched_and_relevered,
    test_weight_cap_and_floor,
    test_distance_is_rms_normalised,
    test_euclidean_and_mahalanobis_both_construct,
    test_hedge_fund_is_unsupported,
    test_deployment_stage_from_vintage,
    test_backtest_runs_and_is_deterministic,
]


def _run_standalone() -> int:
    failures = 0
    for test in ALL_TESTS:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
    print()
    if failures:
        print(f"{failures}/{len(ALL_TESTS)} tests FAILED")
        return 1
    print(f"All {len(ALL_TESTS)} tests passed.")

    h = _holding(sector="Technology", region="US", revenue=20000, ebitda=6000, net_income=3000)
    res = construct_proxy(h, BASELINE, CONFIG)
    print(f"\nProxy for '{h.name}' ({res.confidence} confidence, coverage {res.coverage}):")
    for c in res.comparables:
        print(f"  {c.weight*100:5.1f}%  {c.ticker:<8}{c.name:<26}dist={c.distance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
