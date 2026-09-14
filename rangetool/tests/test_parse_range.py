"""Tests for the range parser DSL."""

from __future__ import annotations

import pytest

from rangetool.range_parser import parse_range


@pytest.mark.parametrize(
    "range_str, expected",
    [
        ("AA", {"AA"}),
        ("AA, KK, AKs", {"AA", "KK", "AKs"}),
        ("AA; KK; AKs", {"AA", "KK", "AKs"}),
        ("TT+", {"TT", "JJ", "QQ", "KK", "AA"}),
        ("22+", {f"{r}{r}" for r in "23456789TJQKA"}),
        # AJs+ → all A-high suited with kicker ≥ J
        ("AJs+", {"AJs", "AQs", "AKs"}),
        # K9s+ → K-high with kicker ≥ 9 PLUS all A-high suited
        ("K9s+", {"K9s", "KTs", "KJs", "KQs"} | {f"A{r}s" for r in "23456789TJQK"}),
        # KQo+ → KQo PLUS all A-high offsuit
        ("KQo+", {"KQo"} | {f"A{r}o" for r in "23456789TJQK"}),
        ("Axo", {f"A{r}o" for r in "23456789TJQK"}),
        ("Axs", {f"A{r}s" for r in "23456789TJQK"}),
        ("Kxs+", {f"K{r}s" for r in "23456789TJQ"}),
        ("Axo, any pair, Kxs+", {*parse_range("Axo"), *parse_range("22+"), *parse_range("Kxs+")}),
        ("  AA ,  KK ", {"AA", "KK"}),
    ],
)
def test_parse_range(range_str: str, expected: set[str]) -> None:
    assert parse_range(range_str) == expected


def test_parse_range_empty() -> None:
    assert parse_range("") == set()
    assert parse_range("   ") == set()


def test_parse_range_invalid_token() -> None:
    with pytest.raises(ValueError):
        parse_range("AA, XYZ")
