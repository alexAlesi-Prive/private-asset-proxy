"""Entrypoint so the service runs via ``python -m engine.service``."""

from engine.service.app import main

if __name__ == "__main__":
    raise SystemExit(main())
