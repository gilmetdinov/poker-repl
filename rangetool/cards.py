"""Card primitives for rangetool.

Provides rank/suit constants, a lightweight immutable Card type, and helpers
for converting to/from the ``treys`` evaluator integer representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import Iterable, List

# Standard 13 ranks, low to high.
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
RANK_INDEX = {rank: idx for idx, rank in enumerate(RANKS)}

# Standard 4 suits.  Order matches treys internals (club=0, diamond=1, heart=2, spade=3)
# but we expose conventional characters.
SUITS = ["c", "d", "h", "s"]
SUIT_INDEX = {suit: idx for idx, suit in enumerate(SUITS)}


@total_ordering
@dataclass(frozen=True, slots=True)
class Card:
    """A single playing card."""

    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANK_INDEX:
            raise ValueError(f"invalid rank: {self.rank!r}")
        if self.suit not in SUIT_INDEX:
            raise ValueError(f"invalid suit: {self.suit!r}")

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card({self.rank!r}, {self.suit!r})"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return (RANK_INDEX[self.rank], SUIT_INDEX[self.suit]) < (
            RANK_INDEX[other.rank],
            SUIT_INDEX[other.suit],
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    @property
    def rank_value(self) -> int:
        """Numeric rank index, 0 for 2 up to 12 for Ace."""
        return RANK_INDEX[self.rank]

    @property
    def suit_value(self) -> int:
        """Numeric suit index matching treys (0..3)."""
        return SUIT_INDEX[self.suit]

    def to_treys(self) -> int:
        """Convert to treys integer card representation."""
        # Import here to keep the module loosely coupled from treys.
        from treys import Card as TreysCard

        return TreysCard.new(str(self))

    @classmethod
    def from_treys(cls, value: int) -> "Card":
        """Create a Card from a treys integer."""
        from treys import Card as TreysCard

        return cls.from_string(TreysCard.int_to_str(value))

    @classmethod
    def from_string(cls, s: str) -> "Card":
        """Parse a card from a 2-character string like 'As' or 'Td'."""
        if len(s) != 2:
            raise ValueError(f"card string must be 2 characters: {s!r}")
        return cls(s[0], s[1])


def make_deck() -> List[Card]:
    """Return the full 52-card deck, sorted."""
    return [Card(rank, suit) for rank in RANKS for suit in SUITS]


DECK = make_deck()


def remove_cards(deck: Iterable[Card], *cards: Card) -> List[Card]:
    """Return a new deck with the given cards removed."""
    excluded = set(cards)
    return [card for card in deck if card not in excluded]
