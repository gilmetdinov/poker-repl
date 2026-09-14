"""Tests for the CLI entry point and calculator mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from rangetool.cli import _run_calculator, main
from rangetool.hands import ALL_HAND_LABELS


def _tiny_matrix() -> dict[str, float]:
    """Return a minimal matrix for fast CLI tests."""
    return {
        "AA|AA": 0.5,
        "AA|KK": 0.82,
        "KK|AA": 0.18,
        "AA|AKs": 0.88,
        "AKs|AA": 0.12,
        "KK|KK": 0.5,
        "KK|AKs": 0.66,
        "AKs|KK": 0.34,
        "AKs|AKs": 0.5,
        "QQ|AA": 0.18,
        "AA|QQ": 0.82,
        "QQ|KK": 0.18,
        "KK|QQ": 0.82,
        "QQ|AKs": 0.54,
        "AKs|QQ": 0.46,
        "QQ|QQ": 0.5,
    }


def test_run_calculator_basic() -> None:
    matrix = _tiny_matrix()
    rows = _run_calculator(["AA", "KK"], "QQ", 0.33, matrix)
    assert len(rows) == 2
    assert rows[0]["hand"] == "AA"
    assert rows[0]["recommendation"] == "PUSH"
    assert rows[1]["hand"] == "KK"
    assert rows[1]["recommendation"] == "PUSH"


def test_run_calculator_show_random(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = _tiny_matrix()

    def fake_equity_vs_random(label: str, mat: dict[str, float]) -> float:
        return 0.55

    monkeypatch.setattr("rangetool.cli.equity_vs_random", fake_equity_vs_random)
    rows = _run_calculator(["AKs"], "QQ", 0.33, matrix, show_random=True)
    assert len(rows) == 1
    assert rows[0]["hand"] == "AKs"
    assert "equity_vs_random" in rows[0]
    assert "delta" in rows[0]


def test_run_calculator_fold_recommendation() -> None:
    matrix = _tiny_matrix()
    rows = _run_calculator(["AKs"], "AA,KK", 0.5, matrix)
    assert rows[0]["recommendation"] == "FOLD"


def test_cli_unknown_hand(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--hands", "XYZ", "--villain-range", "QQ"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "unknown hand label" in captured.err


def test_cli_missing_villain_range(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--hands", "AA"])
    assert exc_info.value.code != 0


def test_cli_empty_cache(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    empty_cache = tmp_path / "empty.json"
    empty_cache.write_text('{"matrix": {}, "random": {}}')
    ret = main(["--cache-path", str(empty_cache), "--top-pct", "25"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Equity cache is empty" in captured.err
