"""Hold'em starting-hand definitions and helpers.

The standard 169-hand grid is built from:
- 13 pocket pairs (AA ... 22)
- 78 suited non-pairs (AKs ... 32s)
- 78 offsuit non-pairs (AKo ... 32o)
"""

from __future__ import annotations

import itertools
from typing import List, Tuple

from rangetool.cards import Card, SUITS

HandLabel = str


def all_hand_labels() -> List[HandLabel]:
    """Return the complete list of 169 starting-hand labels.

    Labels are produced in a consistent deterministic order: all suited variants
    and offsuit variants for each rank pair, followed by all pocket pairs.
    """
    labels: List[HandLabel] = []
    ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
    for i, high in enumerate(ranks):
        for low in ranks[i + 1 :]:
            labels.append(f"{high}{low}s")
            labels.append(f"{high}{low}o")
    for rank in ranks:
        labels.append(f"{rank}{rank}")
    return labels


def classify_label(label: HandLabel) -> str:
    """Return 'pair', 'suited', or 'offsuit' for a hand label."""
    if len(label) not in (2, 3):
        raise ValueError(f"invalid hand label: {label!r}")
    if label[0] == label[1]:
        if len(label) != 2:
            raise ValueError(f"invalid pair label: {label!r}")
        return "pair"
    variant = label[2]
    if variant == "s":
        return "suited"
    if variant == "o":
        return "offsuit"
    raise ValueError(f"invalid hand label: {label!r}")


def num_combos(label: HandLabel) -> int:
    """Number of specific card combinations for a hand label."""
    kind = classify_label(label)
    if kind == "pair":
        return 6  # C(4,2)
    if kind == "suited":
        return 4
    return 12  # offsuit


def _ranks_from_label(label: HandLabel) -> Tuple[str, str]:
    """Return the two ranks of a hand label (high, low)."""
    return label[0], label[1]


def combos_for_label(label: HandLabel) -> List[Tuple[Card, Card]]:
    """Return all specific card combinations matching a hand label.

    Cards within a combo are ordered by descending rank (matching the label).
    """
    kind = classify_label(label)
    rank1, rank2 = _ranks_from_label(label)

    if kind == "pair":
        return [
            (Card(rank1, s1), Card(rank1, s2))
            for s1, s2 in itertools.combinations(SUITS, 2)
        ]

    if kind == "suited":
        return [
            (Card(rank1, suit), Card(rank2, suit)) for suit in SUITS
        ]

    # offsuit
    return [
        (Card(rank1, s1), Card(rank2, s2))
        for s1 in SUITS
        for s2 in SUITS
        if s1 != s2
    ]


def canonical_combo(label: HandLabel) -> Tuple[Card, Card]:
    """Return a canonical specific-card representative for a hand label.

    Because suits are symmetric in heads-up equity against a random/uniform
    range, all specific combos of a label share the same equity.  We pick one
    deterministic representative to reduce the calculation space.
    """
    kind = classify_label(label)
    rank1, rank2 = _ranks_from_label(label)

    if kind == "pair":
        return (Card(rank1, "s"), Card(rank1, "h"))
    if kind == "suited":
        return (Card(rank1, "s"), Card(rank2, "s"))
    return (Card(rank1, "s"), Card(rank2, "d"))


# Cache the complete grid.
ALL_HAND_LABELS = all_hand_labels()
assert len(ALL_HAND_LABELS) == 169, "expected 169 starting-hand labels"
