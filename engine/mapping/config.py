"""Load the versioned mapping configuration (engine/config/mappings.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "mappings.yaml"


def load_mapping_config(path: str | Path | None = None) -> dict[str, Any]:
    """Return the mapping config as a dict. Defaults to the bundled config."""
    config_path = Path(path) if path else _DEFAULT_CONFIG
    with open(config_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)
