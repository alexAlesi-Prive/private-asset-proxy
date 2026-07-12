"""The port (interface) the engine depends on for ingesting holdings.

The engine knows *only* this protocol and :class:`PrivateHolding`. Concrete
sources (EPC today, anything else tomorrow) implement :class:`HoldingSource`.
This is the seam that keeps data-source changes from rippling into the engine.
"""
from __future__ import annotations

from typing import Any, Iterable, Protocol, runtime_checkable

from engine.models.private_holding import PrivateHolding

# A raw, source-shaped holding record (e.g. one EPC row/object) before mapping.
RawHoldingRecord = dict[str, Any]


@runtime_checkable
class HoldingSource(Protocol):
    """Anything that can yield canonical holdings for the engine to consume."""

    def iter_holdings(self) -> Iterable[PrivateHolding]:
        """Yield every holding (private and liquid) as canonical objects."""
        ...

    def iter_private_holdings(self) -> Iterable[PrivateHolding]:
        """Yield only the private/illiquid holdings the proxy engine acts on."""
        ...
