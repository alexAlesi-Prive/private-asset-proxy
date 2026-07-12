"""EPC -> canonical adapter.

This is the ONLY module that knows the shape of an EPC holding record. It maps
raw EPC records onto :class:`PrivateHolding`. When a live EPC endpoint/export is
confirmed, adjust :data:`FIELD_MAP` (and, if fetching live, add a fetch method) —
nothing else in the engine changes.

Design notes
------------
* Field matching is *normalised* (case/space/underscore-insensitive) and each
  canonical field lists several accepted source spellings, so minor EPC naming
  differences do not break ingestion.
* Values are coerced defensively (numbers from strings with %/commas; ISO or
  DD/MM/YYYY dates) and failures degrade to ``None`` rather than raising — an
  unmapped or unparseable optional field must never crash ingestion.
* Every unmapped source key is preserved in ``raw`` for audit and future use.

The mapping table below is *sample-derived and unconfirmed against live EPC*
(see docs/epc-data-contract.md §0). It is intentionally the single point of
change.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from engine.adapters.holding_source import RawHoldingRecord
from engine.models.asset_class import classify
from engine.models.private_holding import PrivateHolding

# Canonical field -> accepted EPC source spellings (matched after normalisation).
# Order within a list is priority order.
FIELD_MAP: dict[str, tuple[str, ...]] = {
    "holding_id": ("symbol", "id", "holdingId", "instrumentId"),
    "name": ("name", "assetName", "instrumentName"),
    "asset_class": ("assetClass", "asset_class", "assetClassType", "class"),
    "currency": ("reportingCurrency", "riskCcy", "risk_ccy", "currency", "ccy",
                 "currencyCode"),
    "region": ("region", "geography", "country"),
    "sector": ("sector", "gicsSector"),
    "last_nav": ("lastNav", "nav", "netAssetValue", "valInRefCcy", "value",
                 "marketValue"),
    "last_nav_date": ("navDate", "lastNavDate", "valuationDate", "asOfDate"),
    "leverage": ("leverage", "grossLeverage"),
    "industry_group": ("industryGroup", "industry_group", "industry"),
    "revenue": ("revenue", "sales"),
    "ebitda": ("ebitda",),
    "net_income": ("netIncome", "net_income", "earnings"),
    "occupancy_rate": ("occupancyRate", "occupancy"),
    "property_type": ("typeOfProperty", "propertyType", "property_type"),
    "expected_yield": ("expectedYield", "yield", "expected_yield"),
    "maturity": ("maturity", "maturityDate"),
    "seniority": ("seniority", "rank"),
    "credit_rating": ("creditRating", "rating", "credit_rating"),
    "strategy_type": ("strategyType", "strategy", "strategy_type"),
    "vintage_year": ("vintageYear", "vintage", "vintage_year"),
}

_NUMERIC_FIELDS = {
    "last_nav", "leverage", "revenue", "ebitda", "net_income",
    "occupancy_rate", "expected_yield",
}
_DATE_FIELDS = {"last_nav_date", "maturity"}
_INT_FIELDS = {"vintage_year"}

# Source keys that identify the holding kind. `Internal` == private/illiquid.
_KEY_TYPE_KEYS = ("keyType", "key_type", "symbolType", "symbol_type")
_PRIVATE_MARKERS = {"internal"}


def _normalise_key(key: str) -> str:
    return key.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    percent = text.endswith("%")
    text = text.rstrip("%").strip()
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100.0 if percent else number


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("iso", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            if fmt == "iso":
                return date.fromisoformat(text[:10])
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _coerce_int(value: Any) -> int | None:
    number = _coerce_number(value)
    return int(number) if number is not None else None


class EpcAdapter:
    """Maps raw EPC records into canonical :class:`PrivateHolding` objects."""

    source_name = "epc"

    def __init__(self, records: list[RawHoldingRecord] | None = None) -> None:
        self._records: list[RawHoldingRecord] = records or []

    # -- construction helpers ------------------------------------------- #
    @classmethod
    def from_json_file(cls, path: str | Path) -> "EpcAdapter":
        """Load records from a JSON export (a list of holding objects).

        Used for sample/export-driven ingestion until a live endpoint exists.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):  # tolerate {"holdings": [...]} envelopes
            for key in ("holdings", "records", "data"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            raise ValueError("EPC export must be a JSON list of holding records")
        return cls(data)

    # -- HoldingSource port --------------------------------------------- #
    def iter_holdings(self) -> Iterable[PrivateHolding]:
        for record in self._records:
            yield self.to_holding(record)

    def iter_private_holdings(self) -> Iterable[PrivateHolding]:
        for record in self._records:
            if self.is_private(record):
                yield self.to_holding(record)

    # -- mapping --------------------------------------------------------- #
    @staticmethod
    def is_private(record: RawHoldingRecord) -> bool:
        """True if the record is a private/illiquid ('Internal') holding."""
        normalised = {_normalise_key(k): v for k, v in record.items()}
        for key in _KEY_TYPE_KEYS:
            value = normalised.get(_normalise_key(key))
            if value and str(value).strip().lower() in _PRIVATE_MARKERS:
                return True
        return False

    def to_holding(self, record: RawHoldingRecord) -> PrivateHolding:
        """Map one raw EPC record to a canonical holding."""
        normalised = {_normalise_key(k): v for k, v in record.items()}
        mapped: dict[str, Any] = {}
        consumed_source_keys: set[str] = set()

        for canonical, sources in FIELD_MAP.items():
            for source in sources:
                nkey = _normalise_key(source)
                if nkey in normalised and normalised[nkey] not in (None, ""):
                    mapped[canonical] = self._coerce(canonical, normalised[nkey])
                    consumed_source_keys.add(nkey)
                    break

        asset_class = classify(mapped.get("asset_class"))
        holding_id = mapped.get("holding_id") or _first_present(
            normalised, ("symbol", "id")
        ) or "UNKNOWN"
        name = mapped.get("name") or holding_id

        return PrivateHolding(
            holding_id=str(holding_id),
            name=str(name),
            asset_class=asset_class,  # type: ignore[arg-type]  # None handled by caller
            currency=_as_str(mapped.get("currency")),
            region=_as_str(mapped.get("region")),
            sector=_as_str(mapped.get("sector")),
            last_nav=mapped.get("last_nav"),
            last_nav_date=mapped.get("last_nav_date"),
            leverage=mapped.get("leverage"),
            industry_group=_as_str(mapped.get("industry_group")),
            revenue=mapped.get("revenue"),
            ebitda=mapped.get("ebitda"),
            net_income=mapped.get("net_income"),
            occupancy_rate=mapped.get("occupancy_rate"),
            property_type=_as_str(mapped.get("property_type")),
            expected_yield=mapped.get("expected_yield"),
            maturity=mapped.get("maturity"),
            seniority=_as_str(mapped.get("seniority")),
            credit_rating=_as_str(mapped.get("credit_rating")),
            strategy_type=_as_str(mapped.get("strategy_type")),
            vintage_year=mapped.get("vintage_year"),
            source=self.source_name,
            raw=dict(record),
        )

    def _coerce(self, canonical: str, value: Any) -> Any:
        if canonical in _NUMERIC_FIELDS:
            return _coerce_number(value)
        if canonical in _DATE_FIELDS:
            return _coerce_date(value)
        if canonical in _INT_FIELDS:
            return _coerce_int(value)
        return value


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_present(normalised: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = normalised.get(_normalise_key(key))
        if value not in (None, ""):
            return value
    return None
