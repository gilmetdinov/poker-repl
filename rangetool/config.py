"""Configuration loading and defaults for the rangetool session REPL."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


def _default_config_path() -> Path:
    """Return the default project-local config path."""
    return Path(__file__).with_name("config.yaml")


@dataclass
class BlindLevel:
    """One blind level in a tournament structure.

    The level stores the chip value of one big blind. Small blind is always
    half of the big blind. The session stores the hero stack in bb, so when
    the level changes the stack in bb is recomputed using the ratio of old
    and new bb chip values.
    """

    level: int
    bb_chips: int
    duration_min: int


@dataclass
class RangePair:
    """A pair of deep-stack and short-stack hand ranges."""

    deep: str
    wide: str


@dataclass
class PositionRangeConfig:
    """Push and call ranges for one hero position."""

    deep_stack_bb: float
    short_stack_bb: float
    desperation_bb: float
    interpolation_curve: str = "threshold"
    tight_until_pct: float = 0.85
    push: RangePair = field(default_factory=lambda: RangePair("", ""))
    call: RangePair = field(default_factory=lambda: RangePair("", ""))


@dataclass
class Thresholds:
    """Equity thresholds for push/limp/fold recommendations."""

    push: float = 0.55
    limp_upper: float = 0.55
    limp_lower: float = 0.42
    ev_margin: float = 0.02
    fold_equity: float = 0.40


@dataclass
class RangetoolConfig:
    """Global configuration for the rangetool session REPL."""

    table_size: int = 3
    starting_stack_bb: int = 15
    blind_schedule: List[BlindLevel] = field(default_factory=list)
    default_ranges: Dict[str, str] = field(default_factory=dict)
    thresholds: Thresholds = field(default_factory=Thresholds)
    hero_ranges: Dict[str, PositionRangeConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.blind_schedule:
            self.blind_schedule = [
                BlindLevel(1, 10, 5),
                BlindLevel(2, 20, 5),
                BlindLevel(3, 30, 5),
                BlindLevel(4, 50, 5),
                BlindLevel(5, 80, 5),
            ]
        if not self.default_ranges:
            self.default_ranges = {
                "BTN": "22+, Axo, Axs, Kxs+, Qxs+, JTs+",
                "SB": "33+, AJo+, AJs+, KQo+, KQs+, QJs+",
                "BB": "22+, Axo, Axs, K8s+, KTo+, Q9s+, QJo, JTs+",
            }
        if not self.hero_ranges:
            self.hero_ranges = {
                "BTN": PositionRangeConfig(
                    deep_stack_bb=15.0,
                    short_stack_bb=2.0,
                    desperation_bb=0.5,
                    interpolation_curve="threshold",
                    tight_until_pct=0.85,
                    push=RangePair(
                        deep="22+, A2s+, A2o+, K8s+, KTo, KJo, KQo, Q9s+, QTo, QJo, JTs, T9s, 98s, 87s, 76s, 65s",
                        wide="22+, A2s+, A2o+, K2s+, KTo+, Q2s+, Q5o+, J4s+, J7o+, T5s+, T7o+, 97s+, 87s, 76s, 65s, 54s",
                    ),
                    call=RangePair(
                        deep="22+, A9s+, AJo+, KQs",
                        wide="22+, A2s+, A8o+, K9s+, KJo+, QTs+",
                    ),
                ),
                "SB": PositionRangeConfig(
                    deep_stack_bb=15.0,
                    short_stack_bb=2.0,
                    desperation_bb=0.5,
                    interpolation_curve="threshold",
                    tight_until_pct=0.85,
                    push=RangePair(
                        deep="22+, A2s+, A2o+, K2s+, K2o+, Q5s+, Q8o+, J8s+, J9o+, T8s+, 98s, 87s, 76s, 65s, 54s",
                        wide="22+, A2s+, A2o+, K2s+, K2o+, Q2s+, Q5o+, J2s+, J6o+, T4s+, T7o+, 95s+, 87s, 76s, 65s, 54s",
                    ),
                    call=RangePair(
                        deep="55+, ATs+, ATo+, KJs+, KQo",
                        wide="22+, A2s+, ATo+, K5s+, KTo+, Q8s+, QJo, JTs",
                    ),
                ),
                "BB": PositionRangeConfig(
                    deep_stack_bb=15.0,
                    short_stack_bb=2.0,
                    desperation_bb=0.5,
                    interpolation_curve="threshold",
                    tight_until_pct=0.85,
                    push=RangePair(
                        deep="22+, A2s+, A2o+, K2s+, K2o+, Q5s+, Q8o+, J8s+, JTo, T8s+, 98s, 87s, 76s",
                        wide="22+, A2s+, A2o+, K2s+, K2o+, Q2s+, Q5o+, J2s+, J6o+, T4s+, T7o+, 95s+, 87s, 76s, 65s, 54s",
                    ),
                    call=RangePair(
                        deep="22+, A2s+, A8o+, K9s+, KJo+, QJs",
                        wide="22+, A2s+, A2o+, K2s+, KTo+, Q8s+, JTs",
                    ),
                ),
            }

    def current_level(self, elapsed_min: int) -> BlindLevel | None:
        """Return the blind level active at the given elapsed time."""
        boundary = 0
        for lvl in self.blind_schedule:
            boundary += lvl.duration_min
            if elapsed_min < boundary:
                return lvl
        return self.blind_schedule[-1] if self.blind_schedule else None

    def get_hero_range_config(self, position: str) -> PositionRangeConfig:
        """Return the position-specific hero range config."""
        return self.hero_ranges.get(position, PositionRangeConfig(
            deep_stack_bb=float(self.starting_stack_bb),
            short_stack_bb=2.0,
            desperation_bb=0.5,
            push=RangePair("22+, AQo+", "22+, Axo, Axs, Kxo, Qxs, Jxs"),
            call=RangePair("22+, AQs+", "22+, Axo, Axs, Kxs+, QTs+"),
        ))


def _migrate_old_blind_level(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old {small_blind, big_blind} format to {bb_chips}."""
    if "big_blind" in item:
        return {
            "level": item.get("level", 0),
            "bb_chips": item.get("big_blind", item.get("bb_chips", 10)),
            "duration_min": item.get("duration_min", 5),
        }
    return item


def _dict_to_blind_levels(data: List[Dict[str, Any]]) -> List[BlindLevel]:
    return [BlindLevel(**_migrate_old_blind_level(item)) for item in data]


def _dict_to_position_range_config(data: Dict[str, Any]) -> PositionRangeConfig:
    return PositionRangeConfig(
        deep_stack_bb=data.get("deep_stack_bb", 15.0),
        short_stack_bb=data.get("short_stack_bb", 2.0),
        desperation_bb=data.get("desperation_bb", 0.5),
        interpolation_curve=data.get("interpolation_curve", "threshold"),
        tight_until_pct=data.get("tight_until_pct", 0.85),
        push=RangePair(**data.get("push", {"deep": "", "wide": ""})),
        call=RangePair(**data.get("call", {"deep": "", "wide": ""})),
    )


def _validate_range_invariants(config: RangetoolConfig) -> None:
    """Ensure call_range ⊆ push_range for every hero position and stack depth."""
    from rangetool.range_parser import parse_range

    for seat, pos_cfg in config.hero_ranges.items():
        push_deep = parse_range(pos_cfg.push.deep)
        call_deep = parse_range(pos_cfg.call.deep)
        missing_deep = call_deep - push_deep
        if missing_deep:
            raise ValueError(
                f"Hero {seat}: call.deep contains hands not in push.deep: "
                f"{sorted(missing_deep)[:10]}..."
            )

        push_wide = parse_range(pos_cfg.push.wide)
        call_wide = parse_range(pos_cfg.call.wide)
        missing_wide = call_wide - push_wide
        if missing_wide:
            raise ValueError(
                f"Hero {seat}: call.wide contains hands not in push.wide: "
                f"{sorted(missing_wide)[:10]}..."
            )


def load_config(path: Path | None = None) -> RangetoolConfig:
    """Load configuration from a YAML file, falling back to defaults."""
    path = path or _default_config_path()
    if not path.exists():
        return RangetoolConfig()

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Detect deprecated short_stack config and ignore it; hero_ranges is now
    # the source of truth for hero push/call ranges.
    if "short_stack" in raw and "hero_ranges" not in raw:
        import warnings

        warnings.warn(
            "'short_stack' is deprecated; define 'hero_ranges' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    thresholds = Thresholds(**raw.get("thresholds", {}))
    blind_schedule = _dict_to_blind_levels(raw.get("blind_schedule", []))

    hero_ranges = {}
    for seat, cfg in raw.get("hero_ranges", {}).items():
        hero_ranges[seat] = _dict_to_position_range_config(cfg)

    config = RangetoolConfig(
        table_size=raw.get("table_size", 3),
        starting_stack_bb=raw.get("starting_stack_bb", 15),
        blind_schedule=blind_schedule,
        default_ranges=raw.get("default_ranges", {}),
        thresholds=thresholds,
        hero_ranges=hero_ranges,
    )

    _validate_range_invariants(config)
    return config


def save_config(config: RangetoolConfig, path: Path | None = None) -> None:
    """Save configuration to a YAML file."""
    path = path or _default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {
        "table_size": config.table_size,
        "starting_stack_bb": config.starting_stack_bb,
        "blind_schedule": [
            {"level": lvl.level, "bb_chips": lvl.bb_chips, "duration_min": lvl.duration_min}
            for lvl in config.blind_schedule
        ],
        "default_ranges": config.default_ranges,
        "thresholds": {
            "push": config.thresholds.push,
            "limp_upper": config.thresholds.limp_upper,
            "limp_lower": config.thresholds.limp_lower,
            "ev_margin": config.thresholds.ev_margin,
            "fold_equity": config.thresholds.fold_equity,
        },
        "hero_ranges": {
            seat: {
                "deep_stack_bb": cfg.deep_stack_bb,
                "short_stack_bb": cfg.short_stack_bb,
                "desperation_bb": cfg.desperation_bb,
                "interpolation_curve": cfg.interpolation_curve,
                "tight_until_pct": cfg.tight_until_pct,
                "push": {"deep": cfg.push.deep, "wide": cfg.push.wide},
                "call": {"deep": cfg.call.deep, "wide": cfg.call.wide},
            }
            for seat, cfg in config.hero_ranges.items()
        },
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="python -m rangetool.config",
        description="Manage rangetool configuration.",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Write the default configuration to rangetool/config.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for --init-config (default: rangetool/config.yaml)",
    )
    args = parser.parse_args()
    if args.init_config:
        path = args.output or _default_config_path()
        save_config(RangetoolConfig(), path)
        print(f"Default config written to {path}")
    else:
        parser.print_help()
