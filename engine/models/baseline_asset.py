"""A traded ("baseline") asset used as a comparable when constructing a proxy.

In production this universe is delivered by the EPC endpoint; in this prototype
it is a fetched sample of ~50 public companies (see engine/data). A baseline
asset is described by the *same* fundamental metrics as a private holding, so
both live in one shared metric space (see engine/mapping).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaselineAsset:
    """A liquid, traded asset with fundamentals used for comparable matching."""

    id: str
    name: str
    ticker: str | None = None
    isin: str | None = None
    asset_class: str = "PublicEquity"
    sector: str | None = None
    region: str | None = None
    currency: str | None = None

    # Fundamentals (financials expressed in a common currency, USD millions, so
    # size metrics are comparable across listings). Margins are derived.
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    market_cap: float | None = None

    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BaselineAsset":
        known = {
            "id", "name", "ticker", "isin", "asset_class", "sector", "region",
            "currency", "revenue", "ebitda", "net_income", "market_cap",
        }
        return cls(
            id=str(d.get("id") or d.get("ticker") or d.get("name")),
            name=str(d.get("name", d.get("id", "unknown"))),
            ticker=d.get("ticker"),
            isin=d.get("isin"),
            asset_class=d.get("asset_class", "PublicEquity"),
            sector=d.get("sector"),
            region=d.get("region"),
            currency=d.get("currency"),
            revenue=_num(d.get("revenue")),
            ebitda=_num(d.get("ebitda")),
            net_income=_num(d.get("net_income")),
            market_cap=_num(d.get("market_cap")),
            raw={k: v for k, v in d.items() if k not in known},
        )


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
