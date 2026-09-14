"""Tests for hand-grid definitions."""

from __future__ import annotations

from rangetool.hands import (
    ALL_HAND_LABELS,
    canonical_combo,
    classify_label,
    combos_for_label,
    num_combos,
)


def test_total_labels() -> None:
    assert len(ALL_HAND_LABELS) == 169


def test_a4o_present() -> None:
    assert "A4o" in ALL_HAND_LABELS
    assert "A4s" in ALL_HAND_LABELS


def test_label_classification() -> None:
    assert classify_label("AA") == "pair"
    assert classify_label("AKs") == "suited"
    assert classify_label("72o") == "offsuit"


def test_num_combos() -> None:
    assert num_combos("AA") == 6
    assert num_combos("AKs") == 4
    assert num_combos("AKo") == 12


def test_combos_for_label() -> None:
    assert len(combos_for_label("AA")) == 6
    assert len(combos_for_label("AKs")) == 4
    assert len(combos_for_label("AKo")) == 12


def test_canonical_combo_deterministic() -> None:
    assert canonical_combo("AKs") == canonical_combo("AKs")
    assert canonical_combo("A4o")[0].rank == "A"
    assert canonical_combo("A4o")[1].rank == "4"
