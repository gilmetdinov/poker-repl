"""Tests for exact equity calculations.

These tests rely on the equity cache.  If the cache is empty, the first run
will compute the required matchups on demand and may take a few seconds per
test.  Run ``python -m rangetool --build-cache`` to precompute everything.
"""

from __future__ import annotations

import pytest

from rangetool.equity import (
    _canonical_matchup,
    equity_vs_random,
    equity_vs_range,
)
from rangetool.hands import ALL_HAND_LABELS
from rangetool.range_parser import parse_range


# Tolerance for published reference numbers.
TOL = 0.005


def test_aa_vs_kk() -> None:
    """AA vs KK heads-up preflop equity should be ~82.6%."""
    eq = _canonical_matchup("AA", "KK")
    assert 0.820 <= eq <= 0.830


def test_aks_vs_qq() -> None:
    """AKs vs QQ heads-up preflop equity should be ~46.0%."""
    eq = _canonical_matchup("AKs", "QQ")
    assert 0.455 <= eq <= 0.465


def test_aa_equity_vs_random() -> None:
    """AA vs a random hand should be ~85.2%."""
    eq = equity_vs_random("AA")
    assert 0.847 <= eq <= 0.857


def test_72o_equity_vs_random() -> None:
    """72o is the weakest offsuit hand vs random, equity ~34.3%."""
    eq = equity_vs_random("72o")
    assert 0.330 <= eq <= 0.350


def test_equity_vs_range_with_card_removal() -> None:
    """AA vs any pair should be very strong; weights must respect card removal."""
    eq = equity_vs_range("AA", parse_range("22+"))
    assert eq > 0.80


def test_all_labels_have_random_equity() -> None:
    """Every label gets a deterministic equity in the valid range."""
    equities = {label: equity_vs_random(label) for label in ALL_HAND_LABELS}
    assert all(0.0 < eq < 1.0 for eq in equities.values())
    assert equities["AA"] > equities["KK"] > equities["QQ"]
    assert equities["72o"] < equities["72s"] < equities["AA"]
