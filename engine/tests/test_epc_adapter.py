"""Smoke + unit tests for the EPC adapter and the canonical holding model.

Runs with pytest, or standalone with zero third-party deps:

    python3 -m engine.tests.test_epc_adapter
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from engine.adapters.epc_adapter import EpcAdapter
from engine.models.asset_class import AssetClassType

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "epc_sample_holdings.json"


def _by_id(adapter: EpcAdapter) -> dict[str, object]:
    return {h.holding_id: h for h in adapter.iter_holdings()}


def test_private_filter_excludes_liquid_and_cash() -> None:
    adapter = EpcAdapter.from_json_file(SAMPLE)
    private = list(adapter.iter_private_holdings())
    ids = {h.holding_id for h in private}
    assert len(private) == 7  # 7 Internal records; ISIN + Cash excluded
    assert "US78462F1030" not in ids  # liquid ETF filtered out
    assert "USD" not in ids            # cash filtered out


def test_direct_private_equity_full_mapping() -> None:
    h = _by_id(EpcAdapter.from_json_file(SAMPLE))["MERIDIAN-GROWTH-III"]
    assert h.asset_class is AssetClassType.DIRECT_PRIVATE_EQUITY
    assert h.currency == "USD"
    assert h.region == "US"
    assert h.revenue == 420_000_000.0
    assert h.ebitda == 95_000_000.0
    assert h.net_income == 38_000_000.0
    assert h.last_nav == 250_000_000.0
    assert h.last_nav_date == date(2026, 3, 31)   # ISO parsed
    assert h.leverage == 1.2
    assert h.vintage_year == 2021
    assert h.is_mappable() and h.validate() == []
    assert h.input_coverage() >= 0.8              # rich record => high coverage
    assert h.source == "epc"
    assert h.raw["symbol"] == "MERIDIAN-GROWTH-III"  # provenance preserved


def test_real_estate_aliases_and_coercions() -> None:
    h = _by_id(EpcAdapter.from_json_file(SAMPLE))["HARBORSTONE-RE-01"]
    assert h.asset_class is AssetClassType.DIRECT_REAL_ESTATE  # "Direct Real Estate"
    assert h.currency == "GBP"                     # mapped from Risk_CCY alias
    assert h.occupancy_rate == 0.93                # "93%" coerced to decimal
    assert h.property_type == "Office"
    assert h.last_nav_date == date(2026, 3, 31)    # DD/MM/YYYY parsed
    assert h.is_mappable()                          # region present => OK


def test_private_debt_yield_alias() -> None:
    h = _by_id(EpcAdapter.from_json_file(SAMPLE))["NORTHWIND-CREDIT"]
    assert h.asset_class is AssetClassType.DIRECT_PRIVATE_DEBT
    assert h.expected_yield == 0.078               # mapped from "yield" alias
    assert h.maturity == date(2029, 6, 30)
    assert h.seniority == "Senior Secured"
    assert h.credit_rating == "BB"
    assert h.is_mappable()


def test_missing_mandatory_routes_to_manual() -> None:
    h = _by_id(EpcAdapter.from_json_file(SAMPLE))["SPARSE-PE-FUND"]
    assert h.asset_class is AssetClassType.PRIVATE_EQUITY_FUND
    assert not h.is_mappable()
    assert "strategy_type" in h.missing_mandatory_inputs()
    codes = {i.code for i in h.validate()}
    assert codes == {"missing_mandatory_input"}


def test_unsupported_class_routes_to_manual() -> None:
    h = _by_id(EpcAdapter.from_json_file(SAMPLE))["EVERGREEN-INFRA"]
    assert h.asset_class is None                    # "Infrastructure" unsupported
    assert not h.has_supported_class()
    assert not h.is_mappable()
    assert h.input_coverage() == 0.0
    assert {i.code for i in h.validate()} == {"unsupported_asset_class"}


ALL_TESTS = [
    test_private_filter_excludes_liquid_and_cash,
    test_direct_private_equity_full_mapping,
    test_real_estate_aliases_and_coercions,
    test_private_debt_yield_alias,
    test_missing_mandatory_routes_to_manual,
    test_unsupported_class_routes_to_manual,
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

    # Human-readable ingestion summary
    adapter = EpcAdapter.from_json_file(SAMPLE)
    print("\nPrivate holdings ingested from EPC sample:")
    print(f"  {'holding_id':<22}{'class':<24}{'mappable':<10}{'coverage'}")
    for h in adapter.iter_private_holdings():
        cls = h.asset_class.value if h.asset_class else "(unsupported)"
        print(f"  {h.holding_id:<22}{cls:<24}{str(h.is_mappable()):<10}{h.input_coverage()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
