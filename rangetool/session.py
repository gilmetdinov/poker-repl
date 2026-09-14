"""Session state for the rangetool REPL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from rangetool.config import RangetoolConfig
from rangetool.hands import ALL_HAND_LABELS
from rangetool.range_parser import parse_range


SEATS_3MAX = ["BTN", "SB", "BB"]
SEATS_HU = ["SB", "BB"]

# Position rotation after each hand. The dealer button moves clockwise, so a
# player who was BTN becomes BB, BB becomes SB, and SB becomes BTN.
ROTATION_3MAX = ["BTN", "BB", "SB"]
ROTATION_HU = ["SB", "BB"]


def _blind_cost_for_position(position: str) -> float:
    """Return the number of bb deducted when a hand starts in ``position``."""
    return {"BTN": 0.0, "SB": 0.5, "BB": 1.0}.get(position, 0.0)


@dataclass
class Session:
    """Mutable state of a single rangetool REPL session."""

    config: RangetoolConfig
    hero_position: str = ""
    active_opponents: Set[str] = field(default_factory=set)
    effective_stack_bb: float | None = None
    elapsed_min: int = 0
    range_overrides: Dict[str, str] = field(default_factory=dict)
    last_hand_index: int = 0
    last_level_bb_chips: int = field(default=0)

    def __post_init__(self) -> None:
        if not self.active_opponents:
            self.active_opponents = set(SEATS_3MAX)
        if self.hero_position and self.hero_position not in self.active_opponents:
            raise ValueError(f"invalid hero position: {self.hero_position}")
        level = self.config.current_level(self.elapsed_min)
        self.last_level_bb_chips = level.bb_chips if level else 10

    @property
    def seats(self) -> List[str]:
        """Return the seat order for the current table size."""
        return SEATS_HU if len(self.active_opponents) == 2 else SEATS_3MAX

    @property
    def is_heads_up(self) -> bool:
        return len(self.active_opponents) == 2

    def set_hero_position(self, seat: str) -> None:
        """Set the hero's current seat."""
        if seat not in self.seats:
            raise ValueError(f"invalid position for current table: {seat!r}")
        self.hero_position = seat

    def knockout(self, seat: str) -> None:
        """Remove an opponent (or the hero, if mis-clicked) from the session."""
        if seat not in self.active_opponents:
            raise ValueError(f"seat not active: {seat!r}")
        self.active_opponents.discard(seat)
        if self.hero_position == seat:
            self.hero_position = ""
        elif self.hero_position and self.hero_position not in self.seats:
            # Table shrank; remap to HU equivalents.
            self.hero_position = "SB" if self.hero_position == "BTN" else "BB"

    def next_hand(self) -> str:
        """Advance hero position for the next hand and return it.

        Blinds are deducted from the effective stack after rotation, because
        the cost is paid when entering the new position (e.g. BTN -> BB costs
        1 bb immediately; SB -> BTN costs nothing).
        """
        if not self.hero_position:
            raise ValueError("hero position not set")
        rotation = ROTATION_HU if self.is_heads_up else ROTATION_3MAX
        idx = rotation.index(self.hero_position)
        self.hero_position = rotation[(idx + 1) % len(rotation)]
        if self.effective_stack_bb is not None:
            cost = _blind_cost_for_position(self.hero_position)
            self.effective_stack_bb = max(0.1, self.effective_stack_bb - cost)
        self.last_hand_index += 1
        return self.hero_position

    def set_level_by_time(self, elapsed_min: int) -> None:
        """Set elapsed time and update the effective stack estimate."""
        self.elapsed_min = max(0, elapsed_min)
        new_level = self.config.current_level(self.elapsed_min)
        self._recompute_stack_for_new_level(new_level)

    def set_level(self, level_number: int) -> None:
        """Set elapsed time to the start of the given blind level."""
        boundary = 0
        for lvl in self.config.blind_schedule:
            if lvl.level == level_number:
                self.elapsed_min = boundary
                self._recompute_stack_for_new_level(lvl)
                return
            boundary += lvl.duration_min
        raise ValueError(f"level {level_number} not found")

    def _recompute_stack_for_new_level(self, new_level) -> None:
        """Recompute effective stack in bb when the blind level changes."""
        if new_level is None:
            return
        if self.effective_stack_bb is None:
            self.effective_stack_bb = float(self.config.starting_stack_bb)
            self.last_level_bb_chips = new_level.bb_chips
            return
        old_bb = self.last_level_bb_chips
        new_bb = new_level.bb_chips
        if old_bb and new_bb and old_bb != new_bb:
            ratio = old_bb / new_bb
            self.effective_stack_bb = round(self.effective_stack_bb * ratio, 2)
        self.last_level_bb_chips = new_level.bb_chips

    def set_stack(self, stack_bb: float) -> None:
        """Manually override the effective stack."""
        if stack_bb <= 0:
            raise ValueError("stack must be greater than 0 bb")
        self.effective_stack_bb = float(stack_bb)

    def set_range_override(self, seat: str, range_str: str) -> None:
        """Override the default villain range for a seat."""
        if seat not in self.seats:
            raise ValueError(f"invalid seat: {seat!r}")
        parsed = parse_range(range_str)
        if not parsed:
            raise ValueError("range parsed to an empty set")
        self.range_overrides[seat] = range_str

    def get_villain_range(self, seat: str) -> Set[str]:
        """Return the parsed villain range for a seat."""
        if seat not in self.seats:
            raise ValueError(f"invalid seat: {seat!r}")
        range_str = self.range_overrides.get(seat, self.config.default_ranges.get(seat, ""))
        return parse_range(range_str)

    def status(self) -> str:
        """Return a human-readable status summary."""
        lines = [
            f"Table: {len(self.active_opponents)}-max",
            f"Hero: {self.hero_position or 'not set'}",
            f"Active seats: {', '.join(self.seats)}",
            f"Effective stack: {self.effective_stack_bb or 'auto'} bb",
            f"Elapsed: {self.elapsed_min} min",
        ]
        level = self.config.current_level(self.elapsed_min)
        if level:
            lines.append(
                f"Blinds: {level.bb_chips // 2}/{level.bb_chips} chips "
                f"(level {level.level}, bb = {level.bb_chips} chips)"
            )
        return "\n".join(lines)
