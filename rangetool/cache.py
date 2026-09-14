"""Persistent cache for precomputed equity values.

The cache stores two artifacts in JSON:
- ``matrix``: a dict mapping ``"label1|label2"`` to the exact equity of the
  canonical combo of ``label1`` versus the canonical combo of ``label2``.
- ``random``: a dict mapping ``label`` to equity_vs_random derived from the
  matrix with proper card-removal weighting.

A missing or partial cache is valid; missing entries are computed on demand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

HandLabel = str


def default_cache_path() -> Path:
    """Return the default equity cache path inside the package output dir."""
    return Path(__file__).with_name("output") / "equity_cache.json"


def load_cache(path: Optional[Path] = None) -> Dict[str, Dict[str, float]]:
    """Load the equity cache from disk.  Returns empty dicts if missing."""
    path = path or default_cache_path()
    if not path.exists():
        return {"matrix": {}, "random": {}}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "matrix": data.get("matrix", {}),
        "random": data.get("random", {}),
    }


def save_cache(
    matrix: Dict[str, float],
    random_eq: Dict[str, float],
    path: Optional[Path] = None,
) -> None:
    """Save the equity cache to disk atomically."""
    path = path or default_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(
            {"matrix": matrix, "random": random_eq},
            f,
            indent=2,
            sort_keys=True,
        )
    tmp.replace(path)


def matrix_key(label1: HandLabel, label2: HandLabel) -> str:
    """Canonical key for a matchup entry."""
    return f"{label1}|{label2}"
