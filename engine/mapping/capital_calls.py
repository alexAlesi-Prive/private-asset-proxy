"""Capital-call (drawdown) economics for commitment-based funds.

A private fund is commitment-based: an LP commits a total amount but only a
fraction is *paid in* (called) at any time; the rest is *uncalled* and subject
to future capital calls. For a **risk/analytics representation** this matters
for sizing, not for comparable selection:

  * Market exposure is carried by the **invested capital** - the marked NAV
    (or paid-in if NAV is absent). That is the notional the proxy basket
    represents.
  * **Uncalled commitment** is NOT market exposure; it is a contingent
    **liquidity obligation** (the LP must be able to fund future calls). A
    capital-call line of credit can cover part of it.

This module derives those figures from the holding's inputs. Pure function; no
effect on which comparables are chosen (that stays driven by fundamentals).

Vintage / J-curve. Vintage year is used *numerically*, not as a categorical
label: a 2024-vintage fund at 20% called behaves nothing like a 2016 vintage at
full deployment. The engine derives fund age and, combined with % called, a
deployment (J-curve) stage - investing → deploying → maturing → harvesting.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.models.private_holding import PrivateHolding


def _f(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _deployment(
    vintage_year: int | None, pct_called: float | None, as_of_year: int
) -> dict[str, Any] | None:
    """Fund age + % called → a J-curve deployment stage (numeric, not categorical).

    The stage blends *time* (age since vintage) and *deployment* (% of commitment
    called), so a young-but-fully-called fund and an old-but-barely-called fund
    are placed correctly rather than by vintage label alone.
    """
    if vintage_year is None and pct_called is None:
        return None
    age = as_of_year - int(vintage_year) if vintage_year is not None else None

    stage = None
    # Deployment dominates when known; age is the fallback / tie-breaker.
    if pct_called is not None:
        if pct_called < 0.30:
            stage = "investing"       # early J-curve: capital going in, fees drag
        elif pct_called < 0.70:
            stage = "deploying"       # ramping exposure
        elif pct_called < 0.95:
            stage = "maturing"        # largely deployed, value being built
        else:
            stage = "harvesting"      # fully called, distributions expected
    elif age is not None:
        if age <= 2:
            stage = "investing"
        elif age <= 4:
            stage = "deploying"
        elif age <= 6:
            stage = "maturing"
        else:
            stage = "harvesting"

    return {
        "vintage_year": int(vintage_year) if vintage_year is not None else None,
        "as_of_year": as_of_year,
        "fund_age_years": age,
        "pct_called": round(pct_called, 6) if pct_called is not None else None,
        "j_curve_stage": stage,
        "note": (
            "Deployment (J-curve) stage from fund age and % called - a young, "
            "lightly-called fund carries little market exposure yet; a fully-called "
            "mature fund behaves like its underlying holdings."
        ),
    }


def summarize_capital_calls(holding: PrivateHolding) -> dict[str, Any] | None:
    """Return a capital-call summary, or ``None`` if no such inputs were given."""
    commitment = _f(holding.commitment)
    line = _f(holding.capital_call_line)

    calls: list[dict[str, Any]] = []
    schedule_total = 0.0
    for raw in holding.capital_calls or []:
        if not isinstance(raw, dict):
            continue
        amount = _f(raw.get("amount"))
        entry = {"date": raw.get("date"), "amount": amount, "purpose": raw.get("purpose")}
        if amount:
            schedule_total += amount
        calls.append(entry)

    # Paid-in: explicit value wins; otherwise fall back to the call schedule sum.
    paid_in = _f(holding.paid_in)
    if paid_in is None and schedule_total > 0:
        paid_in = schedule_total

    # If nothing fund-specific was supplied, don't attach anything.
    if (commitment is None and paid_in is None and line is None and not calls
            and holding.vintage_year is None):
        return None

    uncalled = pct_called = None
    if commitment is not None and paid_in is not None:
        uncalled = round(commitment - paid_in, 6)
        pct_called = round(paid_in / commitment, 6) if commitment else None

    if commitment:
        for entry in calls:
            entry["pct_of_commitment"] = (
                round(entry["amount"] / commitment, 6) if entry["amount"] else None
            )

    # Market-exposed notional the proxy applies to: NAV if marked, else paid-in.
    if holding.last_nav is not None:
        effective_exposure, exposure_basis = holding.last_nav, "nav"
    elif paid_in is not None:
        effective_exposure, exposure_basis = paid_in, "paid_in"
    else:
        effective_exposure, exposure_basis = None, None

    net_uncovered = None
    if uncalled is not None:
        net_uncovered = round(max(uncalled - (line or 0.0), 0.0), 6)

    as_of_year = datetime.now(timezone.utc).year
    deployment = _deployment(holding.vintage_year, pct_called, as_of_year)

    return {
        "commitment": commitment,
        "paid_in": paid_in,
        "uncalled": uncalled,
        "pct_called": pct_called,
        "capital_call_line": line,
        "net_uncovered_commitment": net_uncovered,
        "effective_exposure": effective_exposure,
        "exposure_basis": exposure_basis,
        "deployment": deployment,
        "calls": calls,
        "note": (
            "Market exposure is sized to invested capital "
            f"({'NAV' if exposure_basis == 'nav' else 'paid-in'}); "
            "uncalled commitment is a contingent liquidity obligation, not market exposure."
            if exposure_basis else
            "Provide NAV or paid-in capital to size market exposure."
        ),
    }
