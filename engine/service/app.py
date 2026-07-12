"""HTTP service: JSON API for the proxy engine + serves the built frontend.

Standard-library only. Endpoints:

  GET  /healthz                       liveness
  GET  /api/config                    metrics, mandatory fields, scatter axes, classes
  GET  /api/baseline                  traded comparable universe (with metrics)
  GET  /api/private-assets            saved private holdings (+ proxy summary)
  POST /api/private-assets            add a holding (saves) -> record + proxy
  GET  /api/private-assets/{id}       one holding + its proxy
  DELETE /api/private-assets/{id}     remove a holding
  POST /api/proxy/preview             construct a proxy for inputs WITHOUT saving

Static: anything else is served from the built SPA (``WEB_DIR``) if present,
otherwise a minimal status page. Config via env: PORT (5530), HOST (0.0.0.0),
WEB_DIR, EPC_HOLDINGS_FILE, PRIVATE_ASSETS_FILE.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from engine import __version__
from engine.mapping.config import load_mapping_config
from engine.mapping.proxy_builder import construct_proxy
from engine.mapping.universe import load_baseline_universe
from engine.models.asset_class import MANDATORY_INPUTS, AssetClassType
from engine.models.baseline_asset import BaselineAsset
from engine.mapping.metric_space import extract_metrics
from engine.store.private_asset_store import (
    PrivateAssetStore,
    holding_from_record,
)

logger = logging.getLogger("prive.proxy.service")

DEFAULT_PORT = 5530
DEFAULT_HOST = "0.0.0.0"
_REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    return load_mapping_config()


@lru_cache(maxsize=1)
def get_baseline() -> list[BaselineAsset]:
    return load_baseline_universe()


def get_store() -> PrivateAssetStore:
    return PrivateAssetStore()


def _web_dir() -> Path | None:
    env = os.environ.get("WEB_DIR")
    candidate = Path(env) if env else _REPO_ROOT / "frontend" / "dist"
    return candidate if (candidate / "index.html").is_file() else None


# ---- payload builders ------------------------------------------------------ #
def baseline_payload() -> dict[str, Any]:
    assets = [
        {
            "id": a.id, "name": a.name, "ticker": a.ticker, "sector": a.sector,
            "region": a.region, "currency": a.currency, "metrics": extract_metrics(a),
        }
        for a in get_baseline()
    ]
    return {"source": "prototype-sample", "count": len(assets), "assets": assets}


def config_payload() -> dict[str, Any]:
    cfg = get_config()
    construction = cfg.get("construction", {})
    return {
        "version": cfg.get("version"),
        "metrics": construction.get("metrics", []),
        "scatter": cfg.get("scatter", {}),
        "mandatory_fields": ["name", "asset_class", "currency"],
        "mandatory_note": "At least one financial metric is required to construct a proxy.",
        "asset_classes": [
            {"value": ac.value, "mandatory_inputs": list(MANDATORY_INPUTS[ac])}
            for ac in AssetClassType
        ],
        "metric_fields": [
            "revenue", "ebitda", "net_income", "market_cap", "expected_yield",
            "occupancy_rate",
        ],
    }


def _proxy_for_record(record: dict[str, Any]) -> dict[str, Any]:
    holding = holding_from_record(record)
    return construct_proxy(holding, get_baseline(), get_config()).to_dict()


def _proxy_summary(proxy: dict[str, Any]) -> dict[str, Any]:
    comps = proxy.get("comparables", [])
    return {
        "status": proxy.get("status"),
        "confidence": proxy.get("confidence"),
        "coverage": proxy.get("coverage"),
        "n_comparables": len(comps),
        "top_comparable": comps[0]["name"] if comps else None,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "PriveProxyAsset/" + __version__

    # ---- low-level helpers ------------------------------------------- #
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload, indent=2).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)

    # ---- routing ----------------------------------------------------- #
    def do_OPTIONS(self) -> None:  # CORS preflight
        self._send(204, b"", "text/plain")

    def do_GET(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0].rstrip("/") or "/"
        if route == "/healthz":
            self._json(200, {"status": "ok", "version": __version__})
        elif route == "/api/config":
            self._json(200, config_payload())
        elif route == "/api/baseline":
            self._json(200, baseline_payload())
        elif route == "/api/private-assets":
            self._list_private_assets()
        elif route.startswith("/api/private-assets/"):
            self._get_private_asset(route.rsplit("/", 1)[-1])
        elif route.startswith("/api/"):
            self._json(404, {"error": "not_found", "path": self.path})
        else:
            self._serve_static_or_app(route)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0].rstrip("/") or "/"
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid_json"})
            return
        if route == "/api/private-assets":
            self._add_private_asset(body)
        elif route == "/api/proxy/preview":
            self._preview_proxy(body)
        else:
            self._json(404, {"error": "not_found", "path": self.path})

    def do_PUT(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0].rstrip("/") or "/"
        if not route.startswith("/api/private-assets/"):
            self._json(404, {"error": "not_found", "path": self.path})
            return
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid_json"})
            return
        record = get_store().update(route.rsplit("/", 1)[-1], body)
        if not record:
            self._json(404, {"error": "not_found"})
            return
        self._json(200, {"record": record, "proxy": _proxy_for_record(record)})

    def do_DELETE(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0].rstrip("/") or "/"
        if route.startswith("/api/private-assets/"):
            asset_id = route.rsplit("/", 1)[-1]
            self._json(200, {"ok": get_store().delete(asset_id)})
        else:
            self._json(404, {"error": "not_found", "path": self.path})

    # ---- API endpoints ----------------------------------------------- #
    def _list_private_assets(self) -> None:
        records = get_store().list()
        assets = []
        for record in records:
            try:
                proxy = _proxy_for_record(record)
                summary = _proxy_summary(proxy)
            except Exception:  # a bad record must not break the list
                logger.exception("proxy summary failed for %s", record.get("id"))
                summary = {"status": "error"}
            assets.append({**record, "proxy_summary": summary})
        self._json(200, {"count": len(assets), "assets": assets})

    def _get_private_asset(self, asset_id: str) -> None:
        record = get_store().get(asset_id)
        if not record:
            self._json(404, {"error": "not_found", "id": asset_id})
            return
        self._json(200, {"record": record, "proxy": _proxy_for_record(record)})

    def _add_private_asset(self, body: dict[str, Any]) -> None:
        if not body.get("name"):
            self._json(400, {"error": "missing_field", "field": "name"})
            return
        record = get_store().add(body)
        self._json(201, {"record": record, "proxy": _proxy_for_record(record)})

    def _preview_proxy(self, body: dict[str, Any]) -> None:
        holding = holding_from_record({"id": body.get("id", "preview"), "input": body})
        proxy = construct_proxy(holding, get_baseline(), get_config()).to_dict()
        self._json(200, {"proxy": proxy})

    # ---- static / SPA ------------------------------------------------ #
    def _serve_static_or_app(self, route: str) -> None:
        web = _web_dir()
        if web is None:
            self._status_page()
            return
        rel = route.lstrip("/") or "index.html"
        candidate = (web / rel).resolve()
        if str(candidate).startswith(str(web.resolve())) and candidate.is_file():
            ctype = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self._send(200, candidate.read_bytes(), ctype)
        else:  # SPA fallback
            self._send(200, (web / "index.html").read_bytes(), "text/html; charset=utf-8")

    def _status_page(self) -> None:
        html = _STATUS_PAGE.format(version=__version__, base=len(get_baseline()))
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")


_STATUS_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privé — Proxy-Asset Engine</title>
<style>body{{margin:0;font-family:system-ui,sans-serif;background:#F7F8FA;color:#0F2433}}
header{{background:#fff;border-bottom:1px solid #E2E8F0;padding:20px 32px}}
h1{{margin:0;font-size:20px;color:#0E3C5C}} main{{padding:32px;max-width:760px;margin:0 auto}}
code{{background:#fff;border:1px solid #E2E8F0;padding:2px 6px;border-radius:4px;color:#1F6FA8}}
.badge{{background:#16A34A;color:#fff;border-radius:999px;padding:3px 12px;font-size:12px}}</style>
</head><body><header><h1>Privé — Proxy-Asset Engine</h1></header>
<main><p><span class="badge">● API healthy</span> · v{version}</p>
<p>The frontend build was not found, so this is the API status page.
Baseline universe: <strong>{base}</strong> traded comparables.</p>
<p>API: <code>/api/config</code> · <code>/api/baseline</code> ·
<code>/api/private-assets</code> · <code>/healthz</code></p></main></body></html>
"""


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), Handler)
    web = _web_dir()
    logger.info("Prive Proxy-Asset engine v%s on http://%s:%d (web: %s)",
                __version__, host, port, web or "status-page")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
