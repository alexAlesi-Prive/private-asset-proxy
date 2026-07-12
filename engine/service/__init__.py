"""HTTP service exposing the Proxy-Asset engine (health + read-only views)."""

from engine.service.app import main

__all__ = ["main"]
