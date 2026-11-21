"""Named presets for common 3-max hyper-turbo spots (about 15bb deep).

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
    "3max-hyper-btn": Preset(
        name="3max-hyper-btn",
        villain_range="22+, Axo, Axs, Kxs+, Qxs+, JTs+",
        pot_odds=0.45,
        description="Villain open-shoves from the button (3-max, 15bb).",
    ),
    "3max-hyper-sb": Preset(
        name="3max-hyper-sb",
        villain_range="33+, A2s+, A2o+, K2s+, KQo, QJs",
        pot_odds=0.45,
        description="Villain open-shoves from the small blind (3-max, 15bb).",
    ),
    "3max-hyper-bb": Preset(
        name="3max-hyper-bb",
        villain_range="22+, A2s+, A2o+, K2s+, KTo+, Q2s+, QJo, JTs",
        pot_odds=0.40,
        description="Villain defends or reshoves from the big blind (3-max, 15bb).",
    ),
    "3max-hyper-loose": Preset(
        name="3max-hyper-loose",
        villain_range="22+, Axo, Axs, Kxo, Kxs, Qxo, Qxs, Jxo, Jxs, T9s+",
        pot_odds=0.40,
        description="Very loose shover: any pair, any ace, king, queen or jack, plus T9s.",
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
