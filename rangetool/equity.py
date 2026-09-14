"""Exact heads-up equity calculations for rangetool.

All equities are computed by full combinatorial enumeration over the remaining
board cards (``itertools.combinations``).  To keep the CLI responsive, computed
matchups are cached in ``output/equity_cache.json``.

The evaluator of choice is ``phevaluator`` because its native C-backed lookup
table is significantly faster than pure-Python alternatives.
"""

from __future__ import annotations

import itertools
import multiprocessing as mp
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

from phevaluator import evaluate_cards
from phevaluator.card import Card as PhevalCard

from rangetool.cache import load_cache, matrix_key, save_cache
from rangetool.cards import Card, DECK, remove_cards
from rangetool.hands import (
    ALL_HAND_LABELS,
    canonical_combo,
    combos_for_label,
    HandLabel,
    num_combos,
)


def _card_id(card: Card) -> int:
    """Convert a rangetool Card to a phevaluator integer id."""
    return PhevalCard.to_id(str(card))


def _equity_for_specific_cards(
    my_cards: Tuple[Card, Card], opp_cards: Tuple[Card, Card]
) -> float:
    """Return the exact equity of ``my_cards`` vs ``opp_cards``.

    Enumerates all C(48,5) possible boards from the remaining deck.
    """
    my_ids = (_card_id(my_cards[0]), _card_id(my_cards[1]))
    opp_ids = (_card_id(opp_cards[0]), _card_id(opp_cards[1]))
    deck = [c for c in DECK if c not in my_cards and c not in opp_cards]
    deck_ids = [_card_id(c) for c in deck]

    wins = ties = losses = 0
    for board in itertools.combinations(deck_ids, 5):
        my_rank = evaluate_cards(*my_ids, *board)
        opp_rank = evaluate_cards(*opp_ids, *board)
        if my_rank < opp_rank:
            wins += 1
        elif my_rank == opp_rank:
            ties += 1
        else:
            losses += 1

    total = wins + ties + losses
    return (wins + 0.5 * ties) / total


def _canonical_matchup(label1: HandLabel, label2: HandLabel) -> float:
    """Equity of the canonical combo of ``label1`` vs canonical combo of ``label2``."""
    c1 = canonical_combo(label1)
    c2 = canonical_combo(label2)
    # If the two canonical combos share a card, the matchup is impossible in
    # reality, but for the matrix we still need a value.  Pick an alternative
    # non-overlapping combo for the opponent when this happens.
    if any(card in c2 for card in c1):
        for alt in combos_for_label(label2):
            if all(card not in c1 for card in alt):
                c2 = alt
                break
        else:
            # Should not happen for distinct labels.
            return 0.5
    return _equity_for_specific_cards(c1, c2)


def _compute_matchup(args: Tuple[HandLabel, HandLabel]) -> Tuple[str, float]:
    """Worker helper for multiprocessing."""
    label1, label2 = args
    return matrix_key(label1, label2), _canonical_matchup(label1, label2)


def build_equity_matrix(
    labels: Optional[Iterable[HandLabel]] = None,
    workers: Optional[int] = None,
    cache_path: Optional[Path] = None,
) -> Dict[str, float]:
    """Build and cache the full exact equity matrix for the given labels.

    Args:
        labels: Hand labels to include.  Defaults to all 169 starting hands.
        workers: Number of parallel processes.  Defaults to CPU count.
        cache_path: Path to the cache file.

    Returns:
        The updated matrix dictionary.
    """
    labels = list(labels or ALL_HAND_LABELS)
    cache = load_cache(cache_path)
    matrix = cache["matrix"]

    # Determine missing matchups.  We only compute the upper triangle because
    # equity(B vs A) = 1 - equity(A vs B).  Diagonal entries are exactly 0.5.
    todo: list[Tuple[HandLabel, HandLabel]] = []
    for i, l1 in enumerate(labels):
        key = matrix_key(l1, l1)
        if key not in matrix:
            matrix[key] = 0.5
        for l2 in labels[i + 1 :]:
            key = matrix_key(l1, l2)
            if key not in matrix:
                todo.append((l1, l2))

    if not todo:
        return matrix

    workers = workers or max(1, mp.cpu_count() - 1)
    completed = 0
    total = len(todo)
    print(f"Computing {total} canonical matchups using {workers} workers...", flush=True)

    with mp.Pool(workers) as pool:
        for key, equity in pool.imap_unordered(_compute_matchup, todo, chunksize=1):
            matrix[key] = equity
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"  {completed}/{total} matchups complete", flush=True)
                save_cache(matrix, cache["random"], cache_path)

    print("Deriving equity_vs_random values...", flush=True)
    random_eq = {label: equity_vs_random(label, matrix) for label in ALL_HAND_LABELS}
    save_cache(matrix, random_eq, cache_path)
    return matrix


def _lookup_or_compute(
    label1: HandLabel, label2: HandLabel, matrix: Dict[str, float]
) -> float:
    """Return a matrix entry, computing and caching it if absent."""
    key = matrix_key(label1, label2)
    if key in matrix:
        return matrix[key]

    # Try the symmetric key.
    key_sym = matrix_key(label2, label1)
    if key_sym in matrix:
        equity = 1.0 - matrix[key_sym]
        matrix[key] = equity
        return equity

    equity = _canonical_matchup(label1, label2)
    matrix[key] = equity
    return equity


def _unblocked_combos(
    my_label: HandLabel, villain_label: HandLabel
) -> int:
    """Number of villain combos that do not share a card with my canonical combo."""
    my_cards = canonical_combo(my_label)
    blocked = 0
    for combo in combos_for_label(villain_label):
        if any(card in my_cards for card in combo):
            blocked += 1
    return num_combos(villain_label) - blocked


def equity_vs_random(
    label: HandLabel, matrix: Optional[Dict[str, float]] = None
) -> float:
    """Return exact equity of ``label`` versus a uniformly random hand.

    Uses the cached matrix and applies correct card-removal weighting.
    """
    if matrix is None:
        cache = load_cache()
        matrix = cache["matrix"]
        # If we already have the derived random equity, return it.
        if label in cache.get("random", {}):
            return cache["random"][label]

    my_cards = canonical_combo(label)
    total_weight = 0
    total_equity = 0.0
    for opp_label in ALL_HAND_LABELS:
        weight = _unblocked_combos(label, opp_label)
        if weight <= 0:
            continue
        equity = _lookup_or_compute(label, opp_label, matrix)
        total_equity += equity * weight
        total_weight += weight

    result = total_equity / total_weight if total_weight else 0.0
    return result


def equity_vs_range(
    label: HandLabel,
    villain_labels: Set[HandLabel],
    matrix: Optional[Dict[str, float]] = None,
) -> float:
    """Return exact equity of ``label`` versus a set of villain hand labels.

    Villain combos that share a card with the canonical combo of ``label`` are
    excluded from the weighted average (card removal).
    """
    if matrix is None:
        cache = load_cache()
        matrix = cache["matrix"]

    total_weight = 0
    total_equity = 0.0
    for opp_label in villain_labels:
        weight = _unblocked_combos(label, opp_label)
        if weight <= 0:
            continue
        equity = _lookup_or_compute(label, opp_label, matrix)
        total_equity += equity * weight
        total_weight += weight

    return total_equity / total_weight if total_weight else 0.0
