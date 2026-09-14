"""Command-line interface for rangetool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from rangetool.cache import default_cache_path, load_cache
from rangetool.equity import build_equity_matrix, equity_vs_random, equity_vs_range
from rangetool.hands import ALL_HAND_LABELS, num_combos
from rangetool.presets import get_preset, list_presets
from rangetool.range_parser import parse_range
from rangetool.tierlist import (
    build_tierlist,
    build_villain_overlay,
    filter_tierlist,
    format_console_table,
    write_tierlist_csv,
    write_villain_overlay_csv,
)


def _default_output_dir() -> Path:
    return Path(__file__).with_name("output")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rangetool",
        description="Deterministic 169-hand poker tier-list generator with villain range overlays.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_dir(),
        help="Directory for CSV output (default: rangetool/output/)",
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=default_cache_path(),
        help="Path to the equity cache JSON (default: rangetool/output/equity_cache.json)",
    )
    parser.add_argument(
        "--hands",
        type=str,
        default=None,
        help='Comma-separated specific hands to evaluate vs villain range, e.g. "AKs,AQs,QQ"',
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help='Use a named preset for villain range and pot odds.',
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available presets and exit.",
    )
    parser.add_argument(
        "--villain-range",
        type=str,
        default=None,
        help='Villain range shorthand, e.g. "22+, Axo, Kxs+"',
    )
    parser.add_argument(
        "--pot-odds",
        type=float,
        default=0.33,
        help="Pot-odds threshold for CALL/FOLD recommendation (default: 0.33)",
    )
    parser.add_argument(
        "--show-random",
        action="store_true",
        help="Also show equity_vs_random and delta in calculator mode (slower on partial cache).",
    )
    parser.add_argument(
        "--top-pct",
        type=float,
        default=None,
        help="Export hands whose cumulative percent is <= this value.",
    )
    parser.add_argument(
        "--top-combos",
        type=int,
        default=None,
        help="Export hands whose cumulative combo count is <= this value.",
    )
    parser.add_argument(
        "--build-cache",
        action="store_true",
        help="Precompute the full 169x169 equity matrix and exit.",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Do not print results to stdout; only write CSVs.",
    )
    return parser


def _validate_hand_labels(labels: List[str]) -> None:
    """Ensure every supplied hand label exists in the 169-hand grid."""
    for label in labels:
        if label not in ALL_HAND_LABELS:
            raise ValueError(f"unknown hand label: {label!r}")


def _run_calculator(
    hands: List[str],
    villain_range_str: str,
    pot_odds: float,
    matrix: Dict[str, float],
    show_random: bool = False,
) -> List[dict]:
    """Evaluate specific hands against a villain range."""
    _validate_hand_labels(hands)
    villain_labels = parse_range(villain_range_str)
    if not villain_labels:
        raise ValueError("villain range parsed to an empty set")

    rows = []
    for label in hands:
        eq_range = equity_vs_range(label, villain_labels, matrix)
        row: dict = {
            "hand": label,
            "combos": num_combos(label),
            "equity_vs_villain_range": eq_range,
            "recommendation": "PUSH" if eq_range >= pot_odds else "FOLD",
        }
        if show_random:
            eq_random = equity_vs_random(label, matrix)
            row["equity_vs_random"] = eq_random
            row["delta"] = eq_range - eq_random
        rows.append(row)
    return rows


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_presets:
        for name, preset in list_presets().items():
            print(f"{name}: {preset.description}")
            print(f"  range: {preset.villain_range}")
            print(f"  pot-odds: {preset.pot_odds}")
        return 0

    if args.build_cache:
        build_equity_matrix(cache_path=args.cache_path)
        print("Equity cache built.")
        return 0

    if args.top_pct is not None and args.top_combos is not None:
        parser.error("specify only one of --top-pct or --top-combos")

    if args.preset and args.villain_range:
        parser.error("use either --preset or --villain-range, not both")

    if args.preset:
        preset = get_preset(args.preset)
        args.villain_range = preset.villain_range
        if args.pot_odds == parser.get_default("pot_odds"):
            args.pot_odds = preset.pot_odds

    if args.hands and not args.villain_range:
        parser.error("--hands requires --villain-range (or --preset)")

    # Load the equity cache into memory exactly once per invocation.
    cache = load_cache(args.cache_path)
    matrix = cache["matrix"]

    if not matrix:
        print(
            "Equity cache is empty.  Run first:\n"
            f"  python -m rangetool --build-cache --cache-path {args.cache_path}",
            file=sys.stderr,
        )
        return 1

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.hands:
        try:
            hands = [h.strip() for h in args.hands.split(",")]
            rows = _run_calculator(
                hands, args.villain_range, args.pot_odds, matrix, args.show_random
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        if not args.no_print:
            print(format_console_table(rows))
        return 0

    # Tier-list mode.
    tierlist_path = output_dir / "hand_tierlist.csv"
    tierlist = build_tierlist(matrix)
    filtered = filter_tierlist(tierlist, top_pct=args.top_pct, top_combos=args.top_combos)
    write_tierlist_csv(filtered, tierlist_path)

    if not args.no_print:
        print(format_console_table(filtered))
        print(f"\nWrote {tierlist_path}")

    if args.villain_range:
        overlay_path = output_dir / "tierlist_vs_villain_range.csv"
        overlay = build_villain_overlay(args.villain_range, args.pot_odds, matrix)
        write_villain_overlay_csv(overlay, overlay_path)
        if not args.no_print:
            print("\nVillain overlay:")
            print(format_console_table(overlay))
            print(f"\nWrote {overlay_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
