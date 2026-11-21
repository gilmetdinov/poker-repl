"""Tests for equity cache resolution and the bundled matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from rangetool import cache
from rangetool.hands import ALL_HAND_LABELS


def test_bundled_matrix_is_complete() -> None:
    data = cache.load_cache(cache.bundled_cache_path())
    matrix = data["matrix"]
    # Every ordered pair of the 169 labels, including the diagonal.
    assert len(matrix) == len(ALL_HAND_LABELS) ** 2
    assert set(data["random"]) == set(ALL_HAND_LABELS)


def test_falls_back_to_bundled_when_no_local_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache, "default_cache_path", lambda: tmp_path / "missing.json")
    assert cache.resolve_cache_path() == cache.bundled_cache_path()
    assert cache.load_cache()["matrix"]


def test_local_cache_takes_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local = tmp_path / "equity_cache.json"
    cache.save_cache({"AA|KK": 0.82}, {}, local)
    monkeypatch.setattr(cache, "default_cache_path", lambda: local)
    assert cache.load_cache()["matrix"] == {"AA|KK": 0.82}


def test_explicit_missing_path_is_empty(tmp_path: Path) -> None:
    assert cache.load_cache(tmp_path / "nope.json") == {"matrix": {}, "random": {}}
