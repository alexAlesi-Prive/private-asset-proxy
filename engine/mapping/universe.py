"""Load the baseline universe of traded comparables.

Prototype: reads the bundled JSON sample of ~50 public companies. Production:
this is where the EPC endpoint would be read instead (same return type, so the
rest of the engine is unaffected).
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.models.baseline_asset import BaselineAsset

_DEFAULT_UNIVERSE = Path(__file__).resolve().parents[1] / "data" / "baseline_universe.json"


def load_baseline_universe(path: str | Path | None = None) -> list[BaselineAsset]:
    """Return the baseline traded assets used as proxy comparables."""
    universe_path = Path(path) if path else _DEFAULT_UNIVERSE
    data = json.loads(universe_path.read_text(encoding="utf-8"))
    assets = data["assets"] if isinstance(data, dict) else data
    return [BaselineAsset.from_dict(a) for a in assets]
