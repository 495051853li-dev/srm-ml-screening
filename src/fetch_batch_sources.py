"""Backward-compatible wrapper for the canonical stage4 fetch script."""

from __future__ import annotations

from fetch_sources_stage4 import main


if __name__ == "__main__":
    raise SystemExit(main())
