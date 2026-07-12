"""The engine's canonical typed input model for a private/illiquid holding.

Everything downstream of ingestion — mapping, explanation, validation, UI —
consumes :class:`PrivateHolding`, never a data source's raw shape. Adapters are
responsible for producing these objects (see ``engine/adapters``).

The model is intentionally source-agnostic and dependency-free (stdlib only) so
it runs anywhere and is easy to audit for a regulated client.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from engine.models.asset_class import (
    MANDATORY_INPUTS,
    OPTIONAL_INPUTS,
    AssetClassType,
    relevant_inputs,
)


@dataclass(frozen=True)
class ValidationIssue:
    """A single reason a holding cannot be (fully) auto-mapped."""

    code: str
    message: str


@dataclass
class PrivateHolding:
    """Canonical representation of one private/illiquid holding.

    Fields group into: identity, classification/anchoring, and class-specific
    fundamentals. All fundamentals are optional at the type level; per-class
    *requirements* are enforced by :meth:`missing_mandatory_inputs`, which lets
    the engine route incomplete holdings to manual mapping with a clear reason
    instead of raising.

    ``raw`` preserves the original source record for audit and for fields not
    yet promoted to first-class attributes; ``source`` names the origin
    adapter (e.g. ``"epc"``).
    """

    # --- identity ---
    holding_id: str
    name: str
    asset_class: AssetClassType | None  # None => unrecognised class -> manual mapping

    # --- classification / anchoring ---
    currency: str | None = None            # ISO-4217 reporting currency
    region: str | None = None
    sector: str | None = None
    last_nav: float | None = None          # in `currency`; anchoring/validation only
    last_nav_date: date | None = None
    leverage: float | None = None

    # --- fundamentals: direct equity / real estate ---
    industry_group: str | None = None
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    occupancy_rate: float | None = None    # decimal 0..1
    property_type: str | None = None

    # --- fundamentals: direct debt ---
    expected_yield: float | None = None    # decimal, e.g. 0.065
    maturity: date | None = None
    seniority: str | None = None
    credit_rating: str | None = None

    # --- fundamentals: funds / hedge funds ---
    strategy_type: str | None = None
    vintage_year: int | None = None

    # --- fund commitment / capital calls (optional; commitment-based vehicles) ---
    commitment: float | None = None          # total LP commitment (fund currency)
    paid_in: float | None = None             # cumulative called & contributed capital
    capital_call_line: float | None = None   # available capital-call credit facility
    capital_calls: list | None = None        # [{date, amount, purpose}] drawdown schedule

    # --- provenance ---
    source: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Completeness / validation
    # ------------------------------------------------------------------ #
    def _value(self, canonical_field: str) -> Any:
        return getattr(self, canonical_field, None)

    def has_supported_class(self) -> bool:
        """True when the holding's asset class is one the engine can map."""
        return self.asset_class is not None

    def missing_mandatory_inputs(self) -> list[str]:
        """Mandatory canonical fields (for this class) that are absent/blank.

        Returns an empty list when the class is unknown — validity of an
        unknown-class holding is reported separately by :meth:`validate`.
        """
        if self.asset_class is None:
            return []
        missing = []
        for name in MANDATORY_INPUTS[self.asset_class]:
            value = self._value(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name)
        return missing

    def is_mappable(self) -> bool:
        """True when the class is supported and all its mandatory inputs exist."""
        return self.has_supported_class() and not self.missing_mandatory_inputs()

    def validate(self) -> list[ValidationIssue]:
        """Return the reasons this holding cannot be auto-mapped (empty = OK).

        Non-raising by design: the engine records these on the explanation
        object and sends the holding to manual mapping (methodology §7).
        """
        issues: list[ValidationIssue] = []
        if self.asset_class is None:
            issues.append(
                ValidationIssue(
                    code="unsupported_asset_class",
                    message="Asset class is missing or not supported for auto-mapping",
                )
            )
            return issues
        for missing in self.missing_mandatory_inputs():
            issues.append(
                ValidationIssue(
                    code="missing_mandatory_input",
                    message=(
                        f"Missing mandatory input '{missing}' for "
                        f"{self.asset_class.value}"
                    ),
                )
            )
        return issues

    def available_inputs(self) -> set[str]:
        """Relevant canonical inputs (mandatory+optional) that are populated."""
        if self.asset_class is None:
            return set()
        available = set()
        for name in relevant_inputs(self.asset_class):
            value = self._value(name)
            if value is not None and not (isinstance(value, str) and not value.strip()):
                available.add(name)
        return available

    def input_coverage(self) -> float:
        """Fraction of relevant inputs that are populated (0..1).

        A crude, transparent completeness score that feeds the proxy's
        confidence flag. Mandatory fields are included, so a holding that only
        just clears the mandatory bar still scores low if optional fundamentals
        are absent. An unknown-class holding scores 0.
        """
        if self.asset_class is None:
            return 0.0
        relevant = relevant_inputs(self.asset_class)
        if not relevant:
            return 1.0
        return round(len(self.available_inputs()) / len(relevant), 4)
