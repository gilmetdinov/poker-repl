"""Named presets for common JAQKpot spots.

A preset bundles a villain range and a default pot-odds threshold so the user
can type only their hand at the command line.
"""

from __future__ import annotations

from typing import Dict


class Preset:
    """A named preset bundling villain range and pot odds."""

    def __init__(self, name: str, villain_range: str, pot_odds: float, description: str) -> None:
        self.name = name
        self.villain_range = villain_range
        self.pot_odds = pot_odds
        self.description = description


PRESETS: Dict[str, Preset] = {
    "jaqkpot-btn": Preset(
        name="jaqkpot-btn",
        villain_range="22+, Axo, Axs, Kxs+, Qxs+, JTs+",
        pot_odds=0.45,
        description="Hero on the button vs BTN open/shove range (3-max, 15bb).",
    ),
    "jaqkpot-sb": Preset(
        name="jaqkpot-sb",
        villain_range="33+, AJo+, AJs+, KQo+, KQs+, QJs+",
        pot_odds=0.45,
        description="Hero in the small blind vs SB open/shove range (3-max, 15bb).",
    ),
    "jaqkpot-bb": Preset(
        name="jaqkpot-bb",
        villain_range="22+, Axo, Axs, K8s+, KTo+, Q9s+, QJo, JTs+",
        pot_odds=0.40,
        description="Hero in the big blind vs BB defend/shove range (3-max, 15bb).",
    ),
    "jaqkpot-any2-shove": Preset(
        name="jaqkpot-any2-shove",
        villain_range="22+, Axo, Axs, Kxo, Kxs, Qxo, Qxs, Jxo, Jxs, T9s+",
        pot_odds=0.40,
        description="Opponent shoves any pair, any ace, any broadway, any suited connector.",
    ),
}


def get_preset(name: str) -> Preset:
    """Return a preset by name."""
    if name not in PRESETS:
        raise ValueError(f"unknown preset: {name!r}; available: {list(PRESETS)}")
    return PRESETS[name]


def list_presets() -> Dict[str, Preset]:
    """Return all presets."""
    return PRESETS.copy()
