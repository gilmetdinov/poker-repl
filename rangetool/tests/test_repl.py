"""Tests for the REPL command loop."""

from __future__ import annotations

import pytest

from rangetool import repl as repl_module
from rangetool.config import RangetoolConfig
from rangetool.repl import RangetoolREPL, start_session
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


@pytest.fixture
def fixed_equity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid matrix lookups: every hand has 50% equity vs any range."""
    monkeypatch.setattr(repl_module, "equity_vs_range", lambda label, rng, matrix: 0.5)


@pytest.mark.parametrize("line", ["KTs", "kts", "KTs push", "77"])
def test_bare_hand_is_evaluated(line: str, fixed_equity: None, capsys: pytest.CaptureFixture) -> None:
    session = Session(RangetoolConfig(), hero_position="BTN")
    session.set_stack(10.0)
    RangetoolREPL(session, {}).onecmd(line)
    out = capsys.readouterr().out
    assert "Unknown command" not in out
    assert out.startswith(line.split()[0].upper()[:2])
    assert "Recommendation:" in out


def test_unknown_command(capsys: pytest.CaptureFixture) -> None:
    session = Session(RangetoolConfig(), hero_position="BTN")
    RangetoolREPL(session, {}).onecmd("foo")
    assert "Unknown command: 'foo'" in capsys.readouterr().out


def test_fold_equity_shown_only_for_shove_spots(fixed_equity: None, capsys: pytest.CaptureFixture) -> None:
    session = Session(RangetoolConfig(), hero_position="SB")
    session.set_stack(10.0)
    repl = RangetoolREPL(session, {})
    repl.onecmd("hand AJo")
    assert "fold equity" in capsys.readouterr().out
    repl.onecmd("hand AJo push")
    out = capsys.readouterr().out
    assert "fold equity" not in out.lower()
    assert "EV of calling" in out


def test_start_session_honours_table_size(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_cmdloop(self: RangetoolREPL) -> None:
        captured["session"] = self.session

    monkeypatch.setattr(RangetoolREPL, "cmdloop", fake_cmdloop)
    start_session(table_size=2, stack_bb=10, elapsed_min=0, hero_position="SB")
    session = captured["session"]
    assert session.is_heads_up
    assert session.seats == ["SB", "BB"]
    assert session.hero_position == "SB"
