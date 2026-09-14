"""Tests for session state management."""

from __future__ import annotations

import pytest

from rangetool.config import RangetoolConfig
from rangetool.session import Session


def _default_session() -> Session:
    return Session(RangetoolConfig(), hero_position="BTN")


def test_initial_state() -> None:
    s = _default_session()
    assert s.hero_position == "BTN"
    assert s.seats == ["BTN", "SB", "BB"]
    assert not s.is_heads_up


def test_position_rotation() -> None:
    s = _default_session()
    # Button moves clockwise, so BTN becomes BB, BB becomes SB, SB becomes BTN.
    assert s.next_hand() == "BB"
    assert s.next_hand() == "SB"
    assert s.next_hand() == "BTN"


def test_blind_deduction_on_rotation() -> None:
    s = _default_session()
    s.set_stack(15.0)
    # BTN -> BB: entering BB costs 1 bb immediately.
    assert s.next_hand() == "BB"
    assert s.effective_stack_bb == 14.0
    # BB -> SB: entering SB costs 0.5 bb.
    assert s.next_hand() == "SB"
    assert s.effective_stack_bb == 13.5
    # SB -> BTN: button pays no blind.
    assert s.next_hand() == "BTN"
    assert s.effective_stack_bb == 13.5


def test_knockout_transitions_to_hu() -> None:
    s = _default_session()
    s.knockout("BB")
    assert s.is_heads_up
    assert s.seats == ["SB", "BB"]
    # Hero BTN in 3-max maps to SB in HU.
    assert s.hero_position == "SB"


def test_knockout_invalid_seat() -> None:
    s = _default_session()
    with pytest.raises(ValueError):
        s.knockout("UTG")


def test_set_level_recomputes_stack() -> None:
    s = _default_session()
    s.set_stack(15.0)
    s.set_level(2)  # bb chips doubles from 10 to 20
    assert s.elapsed_min == 5
    assert s.effective_stack_bb == 7.5


def test_set_level_by_time_recomputes_stack() -> None:
    s = _default_session()
    s.set_stack(15.0)
    s.set_level_by_time(12)  # level 3: bb chips 30
    assert s.effective_stack_bb == 5.0


def test_set_decimal_stack() -> None:
    s = _default_session()
    s.set_stack(7.5)
    assert s.effective_stack_bb == 7.5


def test_range_override() -> None:
    s = _default_session()
    s.set_range_override("BTN", "AA, KK")
    rng = s.get_villain_range("BTN")
    assert rng == {"AA", "KK"}
