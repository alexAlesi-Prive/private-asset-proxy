"""Tests for metric-based proxy construction.

Run standalone: python3 -m engine.tests.test_proxy_builder
"""
from __future__ import annotations

import copy

from engine.mapping.config import load_mapping_config
from engine.mapping.proxy_builder import construct_proxy
from engine.mapping.universe import load_baseline_universe
from engine.models.asset_class import AssetClassType
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
    assert abs(total - 1.0) < 1e-6                     # basket sums to 100%
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


ALL_TESTS = [
    test_baseline_loaded,
    test_construct_basic_proxy,
    test_determinism,
    test_single_metric_lowers_confidence,
    test_insufficient_data,
    test_sector_filter_restricts_comparables,
    test_capital_call_summary,
    test_paid_in_defaults_to_schedule_sum,
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
