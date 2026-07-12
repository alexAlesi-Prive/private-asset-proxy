"""Asset-class taxonomy for private holdings and the input fields each class needs.

This module is the single source of truth for:
  * the private asset classes the Proxy-Asset engine supports, and
  * which canonical input fields are *mandatory* vs *optional* per class.

It mirrors the methodology (docs/proxy-methodology.md §2-§3) and is deliberately
decoupled from any data-source shape: adapters translate a source's raw record
into these canonical concepts, never the other way round.
"""
from __future__ import annotations

from enum import Enum


class AssetClassType(str, Enum):
    """Supported private asset classes.

    Values are stable canonical identifiers used throughout the engine, config,
    and audit trail. Human/source spellings are normalised to these via
    :func:`classify`.
    """

    DIRECT_PRIVATE_EQUITY = "DIRECT_PRIVATE_EQUITY"
    DIRECT_PRIVATE_DEBT = "DIRECT_PRIVATE_DEBT"
    DIRECT_REAL_ESTATE = "DIRECT_REAL_ESTATE"
    PRIVATE_EQUITY_FUND = "PRIVATE_EQUITY_FUND"
    PRIVATE_DEBT_FUND = "PRIVATE_DEBT_FUND"
    REAL_ESTATE_FUND = "REAL_ESTATE_FUND"
    HEDGE_FUND = "HEDGE_FUND"


# Canonical input fields that MUST be present for a holding to be auto-mapped.
# A holding missing any of these is routed to manual mapping with an explicit
# reason (methodology §7).
MANDATORY_INPUTS: dict[AssetClassType, tuple[str, ...]] = {
    AssetClassType.DIRECT_PRIVATE_EQUITY: ("region", "sector"),
    AssetClassType.DIRECT_PRIVATE_DEBT: ("region", "sector"),
    AssetClassType.DIRECT_REAL_ESTATE: ("region",),
    AssetClassType.PRIVATE_EQUITY_FUND: ("region", "sector", "strategy_type"),
    AssetClassType.PRIVATE_DEBT_FUND: ("region", "sector", "strategy_type"),
    AssetClassType.REAL_ESTATE_FUND: ("region", "strategy_type"),
    AssetClassType.HEDGE_FUND: ("strategy_type",),
}

# Canonical input fields that SHARPEN the mapping when present but are not
# required. Their coverage feeds the confidence flag on the produced proxy.
OPTIONAL_INPUTS: dict[AssetClassType, tuple[str, ...]] = {
    AssetClassType.DIRECT_PRIVATE_EQUITY: (
        "industry_group", "revenue", "ebitda", "net_income", "currency",
    ),
    AssetClassType.DIRECT_PRIVATE_DEBT: (
        "industry_group", "expected_yield", "maturity", "seniority",
        "credit_rating", "currency",
    ),
    AssetClassType.DIRECT_REAL_ESTATE: (
        "revenue", "ebitda", "net_income", "occupancy_rate", "property_type",
        "currency",
    ),
    AssetClassType.PRIVATE_EQUITY_FUND: ("currency", "vintage_year"),
    AssetClassType.PRIVATE_DEBT_FUND: ("currency", "vintage_year"),
    AssetClassType.REAL_ESTATE_FUND: ("sector", "currency", "vintage_year"),
    AssetClassType.HEDGE_FUND: ("region", "sector", "currency"),
}


def relevant_inputs(asset_class: AssetClassType) -> tuple[str, ...]:
    """All inputs (mandatory + optional) that matter for this class."""
    return MANDATORY_INPUTS[asset_class] + OPTIONAL_INPUTS[asset_class]


# Accepted source spellings that are not simply a normalisation of the enum
# name (e.g. camelCase API forms or abbreviations). Normalisation strips case,
# spaces and underscores, so "Direct Private Equity" / "directPrivateEquity" /
# "DIRECT_PRIVATE_EQUITY" already resolve without an explicit alias.
_ALIASES: dict[str, AssetClassType] = {
    "pefund": AssetClassType.PRIVATE_EQUITY_FUND,
    "pdfund": AssetClassType.PRIVATE_DEBT_FUND,
    "refund": AssetClassType.REAL_ESTATE_FUND,
    "hedgefunds": AssetClassType.HEDGE_FUND,
    "hf": AssetClassType.HEDGE_FUND,
}


def _normalise(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


# Precomputed lookup from normalised enum name -> enum member.
_BY_NORMALISED_NAME: dict[str, AssetClassType] = {
    _normalise(member.value): member for member in AssetClassType
}


def classify(raw_value: str | None) -> AssetClassType | None:
    """Resolve a source asset-class string to an :class:`AssetClassType`.

    Tolerant of case, spacing, underscores/hyphens and common aliases. Returns
    ``None`` for empty input or an unrecognised class (the caller routes such a
    holding to manual mapping rather than guessing).
    """
    if not raw_value:
        return None
    key = _normalise(str(raw_value))
    if key in _BY_NORMALISED_NAME:
        return _BY_NORMALISED_NAME[key]
    return _ALIASES.get(key)
