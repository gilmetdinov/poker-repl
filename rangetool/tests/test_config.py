"""Tests for rangetool configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from rangetool.config import (
    BlindLevel,
    PositionRangeConfig,
    RangePair,
    RangetoolConfig,
    Thresholds,
    load_config,
    save_config,
)


def test_default_config() -> None:
    cfg = RangetoolConfig()
    assert cfg.table_size == 3
    assert cfg.starting_stack_bb == 15
    assert len(cfg.blind_schedule) == 5
    assert "BTN" in cfg.default_ranges
    assert "BTN" in cfg.hero_ranges
    assert cfg.hero_ranges["BTN"].push.deep


def test_blind_level_model() -> None:
    cfg = RangetoolConfig()
    lvl = cfg.current_level(0)
    assert lvl is not None
    assert lvl.level == 1
    assert lvl.bb_chips == 10
    lvl = cfg.current_level(7)
    assert lvl is not None
    assert lvl.level == 2
    assert lvl.bb_chips == 20


def test_save_and_load_config(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    cfg = RangetoolConfig(
        table_size=3,
        starting_stack_bb=15,
        blind_schedule=[BlindLevel(1, 10, 5)],
        default_ranges={"BTN": "22+, Axo"},
        thresholds=Thresholds(push=0.5),
        hero_ranges={
            "BTN": PositionRangeConfig(
                deep_stack_bb=15.0,
                short_stack_bb=2.0,
                desperation_bb=0.5,
                push=RangePair(deep="AA, KK", wide="AA, KK, QQ"),
                call=RangePair(deep="AA", wide="AA, KK"),
            )
        },
    )
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.table_size == 3
    assert loaded.thresholds.push == 0.5
    assert loaded.default_ranges["BTN"] == "22+, Axo"
    hero = loaded.hero_ranges["BTN"]
    assert hero.deep_stack_bb == 15.0
    assert hero.short_stack_bb == 2.0
    assert hero.push.deep == "AA, KK"
    assert hero.push.wide == "AA, KK, QQ"
    assert hero.call.deep == "AA"
    assert hero.desperation_bb == 0.5


def test_old_blind_format_migration(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    raw = """
table_size: 3
starting_stack_bb: 15
blind_schedule:
  - level: 1
    small_blind: 5
    big_blind: 10
    duration_min: 5
hero_ranges:
  BTN:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    push:
      deep: AA
      wide: AA, KK
    call:
      deep: AA
      wide: AA, KK
"""
    path.write_text(raw, encoding="utf-8")
    cfg = load_config(path)
    assert cfg.blind_schedule[0].bb_chips == 10
