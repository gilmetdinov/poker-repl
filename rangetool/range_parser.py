"""Deterministic DSL parser for poker hand ranges.

Supported shorthand (case-insensitive, whitespace around tokens ignored):
- Explicit hands: ``AA, KK, AKs, 72o``
- Pair plus: ``TT+`` (TT and all higher pairs), ``22+`` (any pair)
- Suited/offsuit plus by kicker, standard notation: the high card stays fixed
  and the kicker climbs up to one below it.  ``AJs+`` = AJs, AQs, AKs;
  ``K9s+`` = K9s, KTs, KJs, KQs; ``KQo+`` = KQo only.
- Wildcard kickers: ``Axo`` (all offsuit aces), ``Axs`` (all suited aces)
- Wildcard plus: ``Kxs+`` = every suited hand whose high card is K or higher
  (all suited kings and all suited aces)
- Union: clauses separated by ``,`` or ``;``

Natural-language aliases supported as a convenience:
- ``any pair`` → ``22+``
- ``any Axo`` → ``Axo``
- ``any Axs`` → ``Axs``
- ``any Kxs`` → ``Kxs``
"""

from __future__ import annotations

import re
from typing import Set

from rangetool.cards import RANKS

HandLabel = str

# Order from 2 (index 0) to A (index 12).
_RANK_INDEX = {rank: idx for idx, rank in enumerate(RANKS)}

# Tiny alias map for loose natural-language phrases.
_ALIASES = {
    "any pair": "22+",
    "any axo": "Axo",
    "any axs": "Axs",
    "any kxs": "Kxs",
}

# Regex patterns for token validation.
_PAIR_PLUS_RE = re.compile(r"^([2-9TJQKA])\1\+$")
_NON_PAIR_PLUS_RE = re.compile(r"^([2-9TJQKA])([2-9TJQKA])([so])\+$")
_WILDCARD_RE = re.compile(r"^([2-9TJQKA])x([so])(\+?)$")
_EXPLICIT_PAIR_RE = re.compile(r"^([2-9TJQKA])\1$")
_EXPLICIT_NON_PAIR_RE = re.compile(r"^([2-9TJQKA])([2-9TJQKA])([so])$")


def _normalize_token(token: str) -> str:
    """Upper-case ranks and lower-case the ``x`` wildcard and ``s``/``o`` suffix."""
    return token[:2].upper().replace("X", "x") + token[2:].lower()


def _check_order(high: str, low: str, token: str) -> None:
    """Reject non-pair tokens whose second rank is not below the first."""
    if _RANK_INDEX[low] >= _RANK_INDEX[high]:
        raise ValueError(f"kicker must be lower than high card: {token!r}")


def _expand_pair_plus(rank: str) -> Set[HandLabel]:
    """Expand ``RR+`` into all pairs from RR up to AA."""
    idx = _RANK_INDEX[rank]
    return {r + r for r in RANKS[idx:]}


def _expand_non_pair_plus(high: str, low: str, suitedness: str) -> Set[HandLabel]:
    """Expand ``XYs+`` / ``XYo+`` by raising the kicker with the high card fixed.

    ``KJs+`` yields KJs and KQs; ``ATo+`` yields ATo, AJo, AQo, AKo; ``KQo+``
    yields only KQo.
    """
    high_idx = _RANK_INDEX[high]
    low_idx = _RANK_INDEX[low]
    return {f"{high}{RANKS[k]}{suitedness}" for k in range(low_idx, high_idx)}


def _expand_wildcard(high: str, suitedness: str, plus: bool = False) -> Set[HandLabel]:
    """Expand ``Xxs`` / ``Xxo`` into all suited/offsuit hands with high card X.

    With ``plus`` (``Kxs+``) every higher high card is included as well.
    """
    high_idx = _RANK_INDEX[high]
    highs = RANKS[high_idx:] if plus else [high]
    return {
        f"{h}{kicker}{suitedness}"
        for h in highs
        for kicker in RANKS[: _RANK_INDEX[h]]
    }


def _parse_token(token: str) -> Set[HandLabel]:
    """Parse a single range token into a set of hand labels."""
    token = token.strip()
    if not token:
        return set()

    # Apply simple aliases first.
    lower_token = token.lower()
    if lower_token in _ALIASES:
        token = _ALIASES[lower_token]
    token = _normalize_token(token)

    # Pair plus, e.g. TT+, 22+
    match = _PAIR_PLUS_RE.match(token)
    if match:
        return _expand_pair_plus(match.group(1))

    # Non-pair plus, e.g. AJs+, K9s+
    match = _NON_PAIR_PLUS_RE.match(token)
    if match:
        _check_order(match.group(1), match.group(2), token)
        return _expand_non_pair_plus(match.group(1), match.group(2), match.group(3))

    # Wildcard, e.g. Axo, Axs, Kxs+
    match = _WILDCARD_RE.match(token)
    if match:
        if match.group(1) == "2":
            raise ValueError(f"invalid range token: {token!r}")
        return _expand_wildcard(match.group(1), match.group(2), bool(match.group(3)))

    # Explicit pair, e.g. AA
    match = _EXPLICIT_PAIR_RE.match(token)
    if match:
        return {token}

    # Explicit non-pair, e.g. AKs, 72o
    match = _EXPLICIT_NON_PAIR_RE.match(token)
    if match:
        _check_order(match.group(1), match.group(2), token)
        return {token}

    raise ValueError(f"invalid range token: {token!r}")


def parse_range(range_string: str) -> Set[HandLabel]:
    """Parse a range string into the exact set of 169 hand-grid labels.

    Args:
        range_string: Comma/semicolon separated shorthand description.

    Returns:
        A set of hand labels matching the description.
    """
    if not range_string or not range_string.strip():
        return set()

    result: Set[HandLabel] = set()
    # Split on commas or semicolons.
    for raw_token in re.split(r"[,;]", range_string):
        token = raw_token.strip()
        if not token:
            continue
        result.update(_parse_token(token))
    return result
