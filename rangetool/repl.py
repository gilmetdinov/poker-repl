"""Interactive session REPL for rangetool."""

from __future__ import annotations

import argparse
import cmd
import shlex
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from rangetool.cache import default_cache_path, load_cache
from rangetool.config import RangetoolConfig, load_config
from rangetool.equity import equity_vs_range
from rangetool.hands import ALL_HAND_LABELS, num_combos
from rangetool.session import Session
from rangetool.strategy import recommend


_DEFAULT_ACTION = "open"
_VALID_ACTIONS = {"open", "push", "raise", "limp"}


class RangetoolREPL(cmd.Cmd):
    """Interactive command loop for a rangetool session."""

    intro = (
        "\nRangetool session REPL. Type 'help' for commands, 'quit' to exit.\n"
    )

    def __init__(
        self,
        session: Session,
        matrix: Dict[str, float],
        random_eq: Dict[str, float] | None = None,
        config_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.matrix = matrix
        self.random_eq = random_eq
        self.config_path = config_path
        self.prompt = self._make_prompt()

    def _make_prompt(self) -> str:
        pos = self.session.hero_position or "?"
        stack = self.session.effective_stack_bb
        stack_str = f"{stack:.1f}" if stack is not None else "?"
        return f"({pos}|{stack_str}bb) > "

    def _update_prompt(self) -> None:
        self.prompt = self._make_prompt()

    def _parse_hand_and_action(self, arg: str) -> Tuple[str, str]:
        """Parse "AKs" or "AKs push" into (label, action)."""
        parts = arg.strip().split()
        if not parts:
            raise ValueError("no hand label provided")
        label = parts[0].strip()
        if len(label) == 2:
            normalized = label.upper()
        elif len(label) == 3:
            normalized = label[:2].upper() + label[2:].lower()
        else:
            raise ValueError(f"invalid hand label: {label!r}")
        if normalized not in ALL_HAND_LABELS:
            raise ValueError(f"unknown hand label: {label!r}")

        action = _DEFAULT_ACTION
        if len(parts) > 1:
            action = parts[1].strip().lower()
        if action not in _VALID_ACTIONS:
            raise ValueError(
                f"unknown action: {action!r}; expected one of {_VALID_ACTIONS}"
            )
        return normalized, action

    def _current_villain_range(self) -> set[str]:
        if not self.session.hero_position:
            raise ValueError("hero position not set; use 'pos <BTN|SB|BB>'")
        # In a shove/fold model the villain is the next active seat after hero.
        seats = self.session.seats
        idx = seats.index(self.session.hero_position)
        villain_seat = seats[(idx + 1) % len(seats)]
        return self.session.get_villain_range(villain_seat)

    def _position_range_config(self):
        if not self.session.hero_position:
            raise ValueError("hero position not set; use 'pos <BTN|SB|BB>'")
        return self.session.config.get_hero_range_config(self.session.hero_position)

    def _evaluate_hand(self, label: str, action: str) -> None:
        villain_range = self._current_villain_range()
        equity = equity_vs_range(label, villain_range, self.matrix)
        stack = self.session.effective_stack_bb
        position_range = self._position_range_config()

        pot_odds = None
        villain_bet = 0.0
        pot = 1.5  # blinds (SB 0.5 + BB 1.0)
        if action == "push" and stack is not None:
            villain_bet = stack  # opponent shoved their stack
            pot_odds = stack / (pot + villain_bet + stack) if stack else 0.0

        rec = recommend(
            equity=equity,
            effective_stack_bb=stack,
            position_range=position_range,
            hand_label=label,
            action=action,
            random_eq=self.random_eq,
            pot_odds=pot_odds,
            ev_margin=self.session.config.thresholds.ev_margin,
            fold_equity=self.session.config.thresholds.fold_equity,
        )

        print(f"{label} ({num_combos(label)} combos)")
        print(f"  Hero position: {self.session.hero_position}")
        print(f"  Action: {action}")
        print(f"  Villain range: {self._range_summary(villain_range)}")
        print(f"  Equity vs villain range: {equity:.2%}")
        print(f"  Effective stack: {stack:.1f}bb" if stack is not None else "  Effective stack: unknown")
        if action == "push":
            print(f"  Pot: {pot:.1f} bb  |  Villain bet: {villain_bet:.1f} bb  |  Hero risk: {stack:.1f} bb")
            print(f"  Required equity (pot odds): {pot_odds:.2%}")
        if rec.ev_bb is not None:
            print(f"  EV: {rec.ev_bb:+.2f} bb  |  Fold equity: {self.session.config.thresholds.fold_equity:.0%}")
        print(f"  Range for this spot: {rec.range_size} hands")
        print(f"  Recommendation: {rec.action}")
        print(f"  Reason: {rec.reason}")

    @staticmethod
    def _range_summary(rng: set[str]) -> str:
        n = len(rng)
        return f"{n} hands"

    # Commands ----------------------------------------------------------------

    def do_hand(self, arg: str) -> bool | None:
        """Evaluate a hand: hand <label> [open|push|raise|limp] (default: open)."""
        try:
            label, action = self._parse_hand_and_action(arg)
        except ValueError as exc:
            print(f"Error: {exc}")
            return None
        try:
            self._evaluate_hand(label, action)
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_h(self, arg: str) -> bool | None:
        """Alias for hand."""
        return self.do_hand(arg)

    def do_pos(self, arg: str) -> bool | None:
        """Set hero position: pos <BTN|SB|BB>"""
        seat = arg.strip().upper()
        try:
            self.session.set_hero_position(seat)
            self._update_prompt()
            print(f"Hero position set to {seat}")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_next(self, arg: str) -> bool | None:
        """Advance to the next hand (rotates hero position and deducts blinds)."""
        try:
            new_pos = self.session.next_hand()
            self._update_prompt()
            print(f"Next hand: hero {new_pos}")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_n(self, arg: str) -> bool | None:
        """Alias for next."""
        return self.do_next(arg)

    def do_knockout(self, arg: str) -> bool | None:
        """Knock out an opponent: knockout <BTN|SB|BB>"""
        seat = arg.strip().upper()
        try:
            self.session.knockout(seat)
            self._update_prompt()
            print(f"Knocked out {seat}. Table is now {len(self.session.active_opponents)}-max.")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_ko(self, arg: str) -> bool | None:
        """Alias for knockout."""
        return self.do_knockout(arg)

    def do_stack(self, arg: str) -> bool | None:
        """Override effective stack in bb: stack <bb> (decimals allowed)"""
        try:
            stack = float(arg.strip())
            self.session.set_stack(stack)
            self._update_prompt()
            print(f"Effective stack set to {stack}bb")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_level(self, arg: str) -> bool | None:
        """Set blind level: level <number>"""
        try:
            level = int(arg.strip())
            self.session.set_level(level)
            self._update_prompt()
            print(f"Set to level {level}")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_time(self, arg: str) -> bool | None:
        """Set elapsed tournament time in minutes: time <min>"""
        try:
            minutes = int(arg.strip())
            self.session.set_level_by_time(minutes)
            self._update_prompt()
            print(f"Elapsed time set to {minutes} min")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_range(self, arg: str) -> bool | None:
        """Override villain range for a seat: range <seat> <range>"""
        parts = shlex.split(arg)
        if len(parts) < 2:
            print("Usage: range <BTN|SB|BB> <range shorthand>")
            return None
        seat, range_str = parts[0].upper(), " ".join(parts[1:])
        try:
            self.session.set_range_override(seat, range_str)
            print(f"Range for {seat} set to: {range_str}")
        except ValueError as exc:
            print(f"Error: {exc}")
        return None

    def do_ranges(self, arg: str) -> bool | None:
        """Show current villain ranges by seat."""
        for seat in self.session.seats:
            rng = self.session.get_villain_range(seat)
            source = "override" if seat in self.session.range_overrides else "default"
            print(f"  {seat} [{source}]: {len(rng)} hands")
        return None

    def do_status(self, arg: str) -> bool | None:
        """Show current session status."""
        print(self.session.status())
        return None

    def do_help(self, arg: str) -> bool | None:
        """Show help."""
        return super().do_help(arg)

    def do_quit(self, arg: str) -> bool:
        """Exit the REPL."""
        print("Good luck at the tables.")
        return True

    def do_q(self, arg: str) -> bool:
        """Alias for quit."""
        return self.do_quit(arg)

    def do_exit(self, arg: str) -> bool:
        """Alias for quit."""
        return self.do_quit(arg)

    def emptyline(self) -> None:
        """Ignore empty lines."""
        return None

    def default(self, line: str) -> None:
        """Try to interpret bare words as hand labels."""
        label = line.strip().upper()
        if label in ALL_HAND_LABELS:
            self.do_hand(label)
            return
        print(f"Unknown command: {line!r}. Type 'help' for commands.")


def start_session(
    config_path: Path | None = None,
    cache_path: Path | None = None,
    table_size: int | None = None,
    stack_bb: int | None = None,
    elapsed_min: int | None = None,
    hero_position: str | None = None,
) -> None:
    """Start an interactive rangetool session."""
    config = load_config(config_path)
    cache = load_cache(cache_path or default_cache_path())
    matrix = cache["matrix"]
    if not matrix:
        print("Equity cache is empty. Run first:\n  python -m rangetool --build-cache", file=sys.stderr)
        sys.exit(1)

    print("Starting new rangetool session...")

    # Interactive prompts only for values not supplied via CLI.
    if table_size is None:
        table_size = _ask_int("Table size", config.table_size)
    if elapsed_min is None:
        elapsed_min = _ask_int("Elapsed minutes", 0)
    if stack_bb is None:
        stack_bb = _ask_int("Starting stack bb", config.starting_stack_bb)

    config.table_size = table_size
    config.starting_stack_bb = stack_bb
    session = Session(config)
    session.set_level_by_time(elapsed_min)
    if stack_bb is not None:
        session.set_stack(stack_bb)

    if hero_position:
        session.set_hero_position(hero_position.upper())
    elif sys.stdin.isatty():
        seat_choices = "/".join(session.seats)
        hero_pos = input(f"Hero position ({seat_choices}): ").strip().upper()
        if hero_pos:
            session.set_hero_position(hero_pos)

    RangetoolREPL(session, matrix, cache.get("random"), config_path).cmdloop()


def _ask_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    return int(raw) if raw else default


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python -m rangetool.repl",
        description="Interactive rangetool session REPL.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to rangetool config YAML",
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=None,
        help="Path to equity cache JSON",
    )
    parser.add_argument(
        "--table-size",
        type=int,
        default=None,
        help="Table size (2 or 3)",
    )
    parser.add_argument(
        "--stack-bb",
        type=int,
        default=None,
        help="Starting effective stack in bb",
    )
    parser.add_argument(
        "--elapsed-min",
        type=int,
        default=None,
        help="Elapsed tournament time in minutes",
    )
    parser.add_argument(
        "--hero-position",
        type=str,
        default=None,
        help="Hero starting position (BTN/SB/BB)",
    )
    args = parser.parse_args()
    start_session(
        config_path=args.config,
        cache_path=args.cache_path,
        table_size=args.table_size,
        stack_bb=args.stack_bb,
        elapsed_min=args.elapsed_min,
        hero_position=args.hero_position,
    )
