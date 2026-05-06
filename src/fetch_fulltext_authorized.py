"""Compatibility entrypoint for authorized full-text fetching.

Use this when the current network IP has legal institutional access to some
publisher content. It delegates to ``fetch_fulltext_candidates.py`` and keeps
the same CLI arguments.
"""

from __future__ import annotations

from fetch_fulltext_candidates import main


if __name__ == "__main__":
    raise SystemExit(main())
