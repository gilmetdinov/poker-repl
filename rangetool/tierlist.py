"""Tier-list generation and CSV export."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from rangetool.equity import equity_vs_random, equity_vs_range
from rangetool.hands import ALL_HAND_LABELS, num_combos
from rangetool.range_parser import parse_range

TOTAL_COMBOS = 1326


def _round_pct(value: float) -> float:
    """Round a percentage to two decimal places."""
    return round(value, 2)


def build_tierlist(matrix: Optional[Dict[str, float]] = None) -> List[dict]:
    """Build the full 169-hand tier list sorted by equity vs random.

    Returns a list of dictionaries with keys:
    hand, combos, equity_vs_random, cumulative_combos, cumulative_pct.
    """
    rows = [
        {
            "hand": label,
            "combos": num_combos(label),
            "equity_vs_random": equity_vs_random(label, matrix),
        }
        for label in ALL_HAND_LABELS
    ]
    rows.sort(key=lambda r: r["equity_vs_random"], reverse=True)

    cumulative = 0
    for row in rows:
        cumulative += row["combos"]
        row["cumulative_combos"] = cumulative
        row["cumulative_pct"] = _round_pct(cumulative / TOTAL_COMBOS * 100)

    return rows


def filter_tierlist(
    rows: List[dict],
    top_pct: Optional[float] = None,
    top_combos: Optional[int] = None,
) -> List[dict]:
    """Filter a tier list by cumulative percent or raw combo count."""
    if top_pct is not None and top_combos is not None:
        raise ValueError("specify only one of top_pct or top_combos")

    if top_pct is not None:
        return [row for row in rows if row["cumulative_pct"] <= top_pct]

    if top_combos is not None:
        return [row for row in rows if row["cumulative_combos"] <= top_combos]

    return rows


def write_tierlist_csv(
    rows: List[dict],
    path: Path,
) -> None:
    """Write the tier list to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["hand", "combos", "equity_vs_random", "cumulative_combos", "cumulative_pct"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})


def build_villain_overlay(
    villain_range_str: str,
    pot_odds: float,
    matrix: Optional[Dict[str, float]] = None,
) -> List[dict]:
    """Build the villain-range overlay tier list.

    Returns rows sorted by equity_vs_villain_range descending with columns:
    hand, equity_vs_random, equity_vs_villain_range, delta, recommendation.
    """
    villain_labels = parse_range(villain_range_str)
    if not villain_labels:
        raise ValueError("villain range parsed to an empty set")

    random_equities = {label: equity_vs_random(label, matrix) for label in ALL_HAND_LABELS}
    rows = []
    for label in ALL_HAND_LABELS:
        eq_vs_villain = equity_vs_range(label, villain_labels, matrix)
        delta = eq_vs_villain - random_equities[label]
        recommendation = "CALL" if eq_vs_villain >= pot_odds else "FOLD"
        rows.append(
            {
                "hand": label,
                "equity_vs_random": random_equities[label],
                "equity_vs_villain_range": eq_vs_villain,
                "delta": delta,
                "recommendation": recommendation,
            }
        )

    rows.sort(key=lambda r: r["equity_vs_villain_range"], reverse=True)
    return rows


def write_villain_overlay_csv(rows: List[dict], path: Path) -> None:
    """Write the villain overlay to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "hand",
        "equity_vs_random",
        "equity_vs_villain_range",
        "delta",
        "recommendation",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})


def format_console_table(rows: Iterable[dict], columns: Optional[List[str]] = None) -> str:
    """Pretty-print rows for console output."""
    rows = list(rows)
    if not rows:
        return ""
    columns = columns or list(rows[0].keys())

    # Compute column widths.
    widths = {col: max(len(col), max(len(str(r.get(col, ""))) for r in rows)) for col in columns}

    lines = []
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    lines.append(header)
    lines.append("-" * len(header))
    for row in rows:
        lines.append("  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))
    return "\n".join(lines)


if __name__ == "__main__":
    # Convenience entry point for ``python -m rangetool.tierlist``.
    import sys
    from rangetool.cli import main

    sys.exit(main())
