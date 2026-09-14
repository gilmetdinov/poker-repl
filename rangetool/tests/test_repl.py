"""Tests for the REPL command loop."""

from __future__ import annotations

from rangetool.config import RangetoolConfig
from rangetool.repl import RangetoolREPL
from rangetool.session import Session


def _tiny_matrix() -> dict[str, float]:
    return {
        "AA|KK": 0.82,
        "KK|AA": 0.18,
        "AKs|QQ": 0.46,
        "QQ|AKs": 0.54,
        "77|AKo": 0.39,
        "AKo|77": 0.61,
    }


def test_parse_hand_and_action() -> None:
    session = Session(RangetoolConfig(), hero_position="BTN")
    repl = RangetoolREPL(session, _tiny_matrix())
    assert repl._parse_hand_and_action("AKs") == ("AKs", "open")
    assert repl._parse_hand_and_action("aks push") == ("AKs", "push")
    assert repl._parse_hand_and_action("AA raise") == ("AA", "raise")
    assert repl._parse_hand_and_action("72o limp") == ("72o", "limp")


def test_repl_position_rotation() -> None:
    session = Session(RangetoolConfig(), hero_position="BTN")
    repl = RangetoolREPL(session, _tiny_matrix())
    repl.do_next("")
    assert session.hero_position == "BB"


def test_repl_blind_deduction() -> None:
    session = Session(RangetoolConfig(), hero_position="BTN")
    session.set_stack(10.0)
    repl = RangetoolREPL(session, _tiny_matrix())
    repl.do_next("")  # BTN -> BB, entering BB costs 1 bb
    assert session.hero_position == "BB"
    assert session.effective_stack_bb == 9.0
    repl.do_next("")  # BB -> SB, entering SB costs 0.5 bb
    assert session.hero_position == "SB"
    assert session.effective_stack_bb == 8.5
