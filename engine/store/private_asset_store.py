"""File-backed store for user-added private holdings (prototype persistence).

Records are the raw form inputs (canonical field names) plus an id and
timestamp. In production this would be a database / the platform's holdings
service; a JSON file is enough for the prototype. Path is configurable via
``PRIVATE_ASSETS_FILE`` (default: ``<app>/var/private_assets.json``).
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.models.asset_class import classify
from engine.models.private_holding import PrivateHolding

_LOCK = threading.Lock()

# Numeric input fields coerced to float on the way in.
_NUMERIC_FIELDS = {
    "revenue", "ebitda", "net_income", "market_cap", "last_nav", "leverage",
    "expected_yield", "occupancy_rate", "vintage_year",
    "commitment", "paid_in", "capital_call_line",
}
# String input fields carried through.
_STRING_FIELDS = {
    "name", "asset_class", "currency", "region", "sector", "industry_group",
    "seniority", "credit_rating", "property_type", "strategy_type", "notes",
}


def _default_store_path() -> Path:
    env = os.environ.get("PRIVATE_ASSETS_FILE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "private_assets.json"


def _seed_file() -> Path:
    env = os.environ.get("SEED_PRIVATE_ASSETS_FILE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "data" / "seed_private_assets.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_input(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _NUMERIC_FIELDS:
            num = _num(value)
            if num is not None:
                cleaned[key] = num
        elif key in _STRING_FIELDS:
            if value is not None and str(value).strip():
                cleaned[key] = str(value).strip()
    calls = _clean_capital_calls(payload.get("capital_calls"))
    if calls:
        cleaned["capital_calls"] = calls
    return cleaned


def _clean_capital_calls(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        amount = _num(item.get("amount"))
        date = str(item.get("date")).strip() if item.get("date") else None
        purpose = str(item.get("purpose")).strip() if item.get("purpose") else None
        if amount is None and not date and not purpose:
            continue
        cleaned.append({"date": date, "amount": amount, "purpose": purpose})
    return cleaned


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "asset"


def _seed_records() -> list[dict[str, Any]]:
    """Build seed records (id + timestamp + cleaned input) from the seed file."""
    seed_path = _seed_file()
    try:
        seeds = json.loads(seed_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if not isinstance(seeds, list):
        return []
    records: list[dict[str, Any]] = []
    for item in seeds:
        cleaned = _clean_input(item)
        if not cleaned.get("name"):
            continue
        records.append({
            "id": f"{_slug(cleaned['name'])}-seed",
            "created_at": "2026-07-01T00:00:00+00:00",
            "input": cleaned,
            "seed": True,
        })
    return records


class PrivateAssetStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else _default_store_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """Auto-load the default seed assets whenever the store is empty.

        Empty means the file is missing OR contains no records (``[]``) — both
        happen in fresh containers and after a wipe, so the demo screens are
        always populated on startup. Existing user data is never overwritten.
        """
        if self.path.exists() and self._read():
            return
        seeds = _seed_records()
        with _LOCK:
            # Re-check under lock to avoid double-seeding on concurrent startup.
            if self.path.exists() and self._read():
                return
            self._write(seeds)

    def _read(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def list(self) -> list[dict[str, Any]]:
        return self._read()

    def get(self, asset_id: str) -> dict[str, Any] | None:
        return next((r for r in self._read() if r["id"] == asset_id), None)

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = _clean_input(payload)
        record = {
            "id": f"{_slug(cleaned.get('name', 'asset'))}-{uuid.uuid4().hex[:6]}",
            "created_at": _now(),
            "input": cleaned,
        }
        with _LOCK:
            records = self._read()
            records.append(record)
            self._write(records)
        return record

    def update(self, asset_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Replace a holding's inputs in place (id and created_at preserved)."""
        cleaned = _clean_input(payload)
        with _LOCK:
            records = self._read()
            for record in records:
                if record["id"] == asset_id:
                    record["input"] = cleaned
                    record["updated_at"] = _now()
                    record.pop("seed", None)  # an edited seed is now user data
                    self._write(records)
                    return record
        return None

    def delete(self, asset_id: str) -> bool:
        with _LOCK:
            records = self._read()
            remaining = [r for r in records if r["id"] != asset_id]
            if len(remaining) == len(records):
                return False
            self._write(remaining)
            return True


def holding_from_record(record: dict[str, Any]) -> PrivateHolding:
    """Build a canonical :class:`PrivateHolding` from a stored record or raw input."""
    inp = record.get("input", record)
    return PrivateHolding(
        holding_id=str(record.get("id") or inp.get("name") or "unknown"),
        name=str(inp.get("name") or "Unnamed holding"),
        asset_class=classify(inp.get("asset_class")),
        currency=inp.get("currency"),
        region=inp.get("region"),
        sector=inp.get("sector"),
        industry_group=inp.get("industry_group"),
        revenue=_num(inp.get("revenue")),
        ebitda=_num(inp.get("ebitda")),
        net_income=_num(inp.get("net_income")),
        last_nav=_num(inp.get("last_nav")),
        leverage=_num(inp.get("leverage")),
        expected_yield=_num(inp.get("expected_yield")),
        occupancy_rate=_num(inp.get("occupancy_rate")),
        property_type=inp.get("property_type"),
        seniority=inp.get("seniority"),
        credit_rating=inp.get("credit_rating"),
        strategy_type=inp.get("strategy_type"),
        vintage_year=int(_num(inp.get("vintage_year"))) if _num(inp.get("vintage_year")) else None,
        commitment=_num(inp.get("commitment")),
        paid_in=_num(inp.get("paid_in")),
        capital_call_line=_num(inp.get("capital_call_line")),
        capital_calls=inp.get("capital_calls"),
        source="user",
        raw=inp,
    )
