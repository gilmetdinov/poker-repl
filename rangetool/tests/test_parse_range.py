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
        ("77+", {"77", "88", "99", "TT", "JJ", "QQ", "KK", "AA"}),
        # Non-pair plus: high card fixed, kicker climbs to one below it.
        ("AJs+", {"AJs", "AQs", "AKs"}),
        ("ATo+", {"ATo", "AJo", "AQo", "AKo"}),
        ("K9s+", {"K9s", "KTs", "KJs", "KQs"}),
        ("KJs+", {"KJs", "KQs"}),
        ("KQo+", {"KQo"}),
        ("54s+", {"54s"}),
        ("Axo", {f"A{r}o" for r in "23456789TJQK"}),
        ("Axs", {f"A{r}s" for r in "23456789TJQK"}),
        ("Kxs", {f"K{r}s" for r in "23456789TJQ"}),
        # Wildcard plus: high card K or better.
        ("Kxs+", {f"K{r}s" for r in "23456789TJQ"} | {f"A{r}s" for r in "23456789TJQK"}),
        ("Qxo+", {f"Q{r}o" for r in "23456789TJ"}
                 | {f"K{r}o" for r in "23456789TJQ"}
                 | {f"A{r}o" for r in "23456789TJQK"}),
        # Case-insensitive.
        ("aks, kqo+, 77+", {"AKs", "KQo"} | {f"{r}{r}" for r in "789TJQKA"}),
        ("kXs", {f"K{r}s" for r in "23456789TJQ"}),
        ("Axo, any pair, Kxs+", {*parse_range("Axo"), *parse_range("22+"), *parse_range("Kxs+")}),
        ("  AA ,  KK ", {"AA", "KK"}),
    ],
)
def test_parse_range(range_str: str, expected: set[str]) -> None:
    assert parse_range(range_str) == expected


def test_parse_range_empty() -> None:
    assert parse_range("") == set()
    assert parse_range("   ") == set()


@pytest.mark.parametrize("bad", ["AA, XYZ", "KAs", "AAs", "KAs+", "2xs", "AK"])
def test_parse_range_invalid_token(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_range(bad)
