"""Poker hand evaluation using the lookup-table-based ``treys`` library."""

from __future__ import annotations

from treys import Card as TreysCard
from treys import Evaluator

from rangetool.cards import Card

_EVALUATOR = Evaluator()


def evaluate_seven(*cards: Card) -> int:
    """Evaluate the best 5-card hand from exactly 7 cards.

    Returns a treys rank integer.  Lower numbers mean stronger hands.
    """
    if len(cards) != 7:
        raise ValueError(f"expected 7 cards, got {len(cards)}")
    treys_cards = [c.to_treys() for c in cards]
    return _EVALUATOR.evaluate(treys_cards, [])


def card_to_str(card: Card) -> str:
    """Pretty-print a card using treys notation (e.g. 'Ah')."""
    return TreysCard.int_to_str(card.to_treys())


def rank_to_class(rank: int) -> str:
    """Return the human-readable hand class for a treys rank integer."""
    return _EVALUATOR.class_to_string(_EVALUATOR.get_rank_class(rank))
