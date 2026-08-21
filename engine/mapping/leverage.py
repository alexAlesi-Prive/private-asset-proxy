"""Capital-structure (Hamada) beta relevering for the proxy basket.

Standard comparable-company practice does not compare a levered private holding
to a listed comp at face value: a sponsor-backed deal running at 4–6x net
debt/EBITDA has a very different *equity* beta from a listed comparable at 1–2x,
purely because of capital structure. The accepted correction is to **unlever**
each comparable's equity beta to an asset (unlevered) beta and **relever** it to
the holding's own leverage — the Hamada relation:

    βL = βU · [ 1 + (1 − t) · (D/E) ]

Two things address the reviewer's point:

1. ``leverage`` (net debt / EBITDA) is now a *matching* metric (see
   ``metric_space``), so comparables are chosen with a similar capital structure
   in the first place.
2. Residual differences are reported here as a **relever factor** the analytics
   stack can apply to the proxy basket's equity beta:

       relever_factor = [1 + (1 − t)·(D/E)_holding] / [1 + (1 − t)·(D/E)_basket]

This is a *reported adjustment*, not a re-selection of comparables. Pure
function; no I/O. Returns ``None`` when the inputs needed to compute it are
absent (leverage stays available as a matching metric regardless).
"""
from __future__ import annotations

from typing import Any, Sequence

from engine.models.private_holding import PrivateHolding

# Below this the debt-shielded denominator is treated as unreliable (extreme net
# cash), and no relever factor is reported.
_MIN_DENOM = 0.05


def _holding_net_debt(holding: PrivateHolding) -> float | None:
    """Net debt for the holding: explicit, else implied by leverage × EBITDA."""
    if holding.net_debt is not None:
        return float(holding.net_debt)
    if holding.leverage is not None and holding.ebitda not in (None, 0):
        return float(holding.leverage) * float(holding.ebitda)
    return None


def _holding_equity(holding: PrivateHolding) -> float | None:
    """Equity value for the holding: NAV is the private-equity value."""
    if holding.last_nav is not None:
        return float(holding.last_nav)
    return None


def summarize_leverage(
    holding: PrivateHolding,
    comparables: Sequence[Any],
    tax_rate: float = 0.25,
) -> dict[str, Any] | None:
    """Report the Hamada equity-beta relevering of the basket to the holding.

    ``comparables`` are :class:`~engine.mapping.proxy_builder.Comparable`-like
    objects carrying ``weight`` and a ``metrics`` dict (with ``net_debt`` and
    ``market_value``). Returns ``None`` if neither side yields a usable D/E.
    """
    t = float(tax_rate)

    nd = _holding_net_debt(holding)
    eq = _holding_equity(holding)
    holding_de = (nd / eq) if (nd is not None and eq not in (None, 0)) else None
    holding_lev = (
        nd / float(holding.ebitda)
        if nd is not None and holding.ebitda not in (None, 0) and holding.ebitda > 0
        else None
    )

    # Weighted-average D/E and leverage of the basket comparables.
    de_num = de_wsum = lev_num = lev_wsum = 0.0
    for comp in comparables:
        metrics = getattr(comp, "metrics", {}) or {}
        weight = float(getattr(comp, "weight", 0.0) or 0.0)
        c_nd = metrics.get("net_debt")
        c_eq = metrics.get("market_value")
        if c_nd is not None and c_eq not in (None, 0):
            de_num += weight * (c_nd / c_eq)
            de_wsum += weight
        c_lev = metrics.get("leverage")
        if c_lev is not None:
            lev_num += weight * c_lev
            lev_wsum += weight
    basket_de = de_num / de_wsum if de_wsum > 0 else None
    basket_lev = lev_num / lev_wsum if lev_wsum > 0 else None

    relever_factor = None
    if holding_de is not None and basket_de is not None:
        denom = 1.0 + (1.0 - t) * basket_de
        if abs(denom) >= _MIN_DENOM:
            relever_factor = round((1.0 + (1.0 - t) * holding_de) / denom, 4)

    if holding_de is None and basket_de is None and holding_lev is None and basket_lev is None:
        return None

    if relever_factor is None:
        note = (
            "Leverage used for matching; supply net debt (or a leverage multiple) "
            "and NAV on the holding to relever the proxy's equity beta (Hamada)."
        )
    elif relever_factor > 1.02:
        note = (
            f"Holding is more levered than its comparables → proxy equity beta "
            f"scaled up ×{relever_factor:.2f} (Hamada relevering, t={t:.0%})."
        )
    elif relever_factor < 0.98:
        note = (
            f"Holding is less levered than its comparables → proxy equity beta "
            f"scaled down ×{relever_factor:.2f} (Hamada relevering, t={t:.0%})."
        )
    else:
        note = (
            f"Holding leverage ≈ comparables → equity-beta relevering is "
            f"immaterial (×{relever_factor:.2f})."
        )

    return {
        "marginal_tax_rate": round(t, 4),
        "holding_net_debt": round(nd, 4) if nd is not None else None,
        "holding_equity": round(eq, 4) if eq is not None else None,
        "holding_debt_to_equity": round(holding_de, 4) if holding_de is not None else None,
        "holding_leverage": round(holding_lev, 4) if holding_lev is not None else None,
        "basket_debt_to_equity": round(basket_de, 4) if basket_de is not None else None,
        "basket_leverage": round(basket_lev, 4) if basket_lev is not None else None,
        "relever_factor": relever_factor,
        "note": note,
    }
