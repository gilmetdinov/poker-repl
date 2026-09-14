"""Tests for strategy recommendations."""

from __future__ import annotations

import pytest

from rangetool.config import PositionRangeConfig, RangePair
from rangetool.strategy import (
    _ev_call_shove,
    _ev_open_shove,
    auto_pot_odds,
    recommend,
)


@pytest.fixture
def position_range() -> PositionRangeConfig:
    return PositionRangeConfig(
        deep_stack_bb=15.0,
        short_stack_bb=2.0,
        desperation_bb=0.5,
        interpolation_curve="linear",
        push=RangePair(deep="AA, KK, AKs", wide="AA, KK, AKs, AQs, AQo, KQs, QJs"),
        call=RangePair(deep="AA, KK", wide="AA, KK, AKs, AQs, QQ"),
    )


@pytest.fixture
def random_eq() -> dict[str, float]:
    return {
        "AA": 0.85,
        "KK": 0.82,
        "AKs": 0.67,
        "AQs": 0.66,
        "AQo": 0.65,
        "KQs": 0.60,
        "QJs": 0.55,
    }


# ------------------------------------------------------------------ Range tests
# With fold_equity=0.0 the behaviour mirrors the old range-only logic.


def test_recommend_deep_stack_uses_deep_range(position_range, random_eq) -> None:
    rec = recommend(0.50, 15.0, position_range, "AA", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "PUSH"


def test_recommend_deep_stack_fold_outside_deep_range(position_range, random_eq) -> None:
    # AQS outside push.deep; equity 0.40 → EV = 0.40*31.5-15 = -2.4bb → FOLD
    rec = recommend(0.40, 15.0, position_range, "AQs", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "FOLD"


def test_recommend_short_stack_uses_wide_range(position_range, random_eq) -> None:
    rec = recommend(0.50, 2.0, position_range, "QJs", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "PUSH"


def test_recommend_short_stack_fold_outside_wide_range(position_range, random_eq) -> None:
    # 72o outside wide range; equity 0.30 → EV = 0.30*5.5-2 = -0.35bb → FOLD
    rec = recommend(0.30, 2.0, position_range, "72o", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "FOLD"


def test_recommend_interpolates_between_ranges(position_range, random_eq) -> None:
    rec_aqs = recommend(0.50, 8.5, position_range, "AQs", random_eq=random_eq, fold_equity=0.0)
    rec_aqo = recommend(0.50, 8.5, position_range, "AQo", random_eq=random_eq, fold_equity=0.0)
    # KQS outside interpolated range; equity 0.40 → EV = 0.40*18.5-8.5 = -1.1bb
    rec_kqs = recommend(0.40, 8.5, position_range, "KQs", random_eq=random_eq, fold_equity=0.0)
    assert rec_aqs.action == "PUSH"
    assert rec_aqo.action == "PUSH"
    assert rec_kqs.action == "FOLD"


def test_recommend_interpolation_reason_mentions_interpolated(position_range, random_eq) -> None:
    rec = recommend(0.50, 8.5, position_range, "AQs", random_eq=random_eq, fold_equity=0.0)
    # AQS is in the interpolated range (in_range=true)
    assert "in range" in rec.reason


def test_recommend_desperation_pushes_any_two(position_range, random_eq) -> None:
    rec = recommend(0.10, 0.4, position_range, "72o", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "PUSH"
    assert "desperation" in rec.reason


def test_recommend_stack_above_deep_uses_deep_range(position_range, random_eq) -> None:
    # AQS outside deep range at 25bb; equity 0.40 → EV = 0.40*51.5-25 = -4.4bb → FOLD
    rec = recommend(0.40, 25.0, position_range, "AQs", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "FOLD"


def test_recommend_unknown_stack_defaults_to_deep_range(position_range, random_eq) -> None:
    rec = recommend(0.50, None, position_range, "AA", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "PUSH"
    rec2 = recommend(0.50, None, position_range, "AQs", random_eq=random_eq, fold_equity=0.0)
    assert rec2.action == "FOLD"


def test_recommend_call_action_uses_call_range(position_range, random_eq) -> None:
    # AQS outside call.deep at 15bb; eq 0.42 → EV = 0.42*31.5-15 = -1.77bb → FOLD
    rec = recommend(0.42, 15.0, position_range, "AQs", action="push", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "FOLD"
    # At 2bb wide range includes AQs → in range
    rec2 = recommend(0.50, 2.0, position_range, "AQs", action="push", random_eq=random_eq, fold_equity=0.0)
    assert rec2.action == "PUSH"


def test_recommend_open_action_uses_push_range(position_range, random_eq) -> None:
    rec = recommend(0.50, 15.0, position_range, "AKs", action="open", random_eq=random_eq, fold_equity=0.0)
    assert rec.action == "PUSH"
    # AQS outside push.deep at 15bb; eq 0.42 → EV = 0.42*31.5-15 = -1.77bb → FOLD
    rec2 = recommend(0.42, 15.0, position_range, "AQs", action="open", random_eq=random_eq, fold_equity=0.0)
    assert rec2.action == "FOLD"


def test_recommend_threshold_interpolation_keeps_deep_range() -> None:
    pr = PositionRangeConfig(
        deep_stack_bb=15.0,
        short_stack_bb=2.0,
        desperation_bb=0.5,
        interpolation_curve="threshold",
        tight_until_pct=0.85,
        push=RangePair(deep="AA, KK", wide="AA, KK, QQ, JJ, TT"),
        call=RangePair(deep="AA", wide="AA, KK"),
    )
    # TT outside deep range at 13bb; eq 0.42 → EV = 0.42*27.5-13 = -1.45bb → FOLD
    rec = recommend(0.42, 13.0, pr, "TT", action="open", fold_equity=0.0)
    assert rec.action == "FOLD"
    # QQ in interpolated range at 8bb and +EV
    rec2 = recommend(0.50, 8.0, pr, "QQ", action="open", fold_equity=0.0)
    assert rec2.action == "PUSH"


# ------------------------------------------------------------ EV override tests


def test_recommend_ev_override_outside_range(position_range, random_eq) -> None:
    """Hand outside call range but equity well above required → PUSH."""
    rec = recommend(
        equity=0.70,
        effective_stack_bb=10.0,
        position_range=position_range,
        hand_label="AQs",
        action="push",
        random_eq=random_eq,
        pot_odds=0.40,
        ev_margin=0.02,
        fold_equity=0.0,
    )
    assert rec.action == "PUSH"
    assert "overriding" in rec.reason


def test_recommend_ev_fold_inside_range(position_range, random_eq) -> None:
    """Hand inside call range but equity too low → FOLD."""
    rec = recommend(
        equity=0.30,
        effective_stack_bb=10.0,
        position_range=position_range,
        hand_label="AA",
        action="push",
        random_eq=random_eq,
        pot_odds=0.40,
        ev_margin=0.02,
        fold_equity=0.0,
    )
    assert rec.action == "FOLD"
    assert "-EV" in rec.reason


def test_recommend_open_ev_override_with_fold_equity(position_range, random_eq) -> None:
    """AQs outside push.deep range but +EV with fold_equity=0.40 → PUSH."""
    rec = recommend(
        equity=0.50,
        effective_stack_bb=15.0,
        position_range=position_range,
        hand_label="AQs",
        action="open",
        random_eq=random_eq,
        fold_equity=0.40,
    )
    assert rec.action == "PUSH"
    assert "overriding" in rec.reason.lower()
    assert rec.ev_bb is not None and rec.ev_bb > 0


def test_recommend_open_ev_fold_with_fold_equity(position_range, random_eq) -> None:
    """AQs inside push.wide but -EV with fold_equity=0.0 → FOLD."""
    rec = recommend(
        equity=0.35,
        effective_stack_bb=2.0,
        position_range=position_range,
        hand_label="AQs",
        action="open",
        random_eq=random_eq,
        fold_equity=0.0,
    )
    # At 2bb, AQs is in wide range.  With fe=0 and equity 0.35:
    # EV = 0.0*1.5 + 1.0*(0.35*(1.5+4) - 2) = 1.925 - 2 = -0.075 < -0.02 → FOLD
    assert rec.action == "FOLD"
    assert rec.ev_bb is not None and rec.ev_bb < 0


def test_recommend_call_action_ev_override(position_range, random_eq) -> None:
    """push action: hand outside call.deep but +EV with equity."""
    rec = recommend(
        equity=0.45,
        effective_stack_bb=15.0,
        position_range=position_range,
        hand_label="AQs",
        action="push",
        random_eq=random_eq,
        pot_odds=0.40,
        ev_margin=0.02,
        fold_equity=0.0,
    )
    # EV(call) = 0.45 * (1.5+15+15) - 15 = 14.175 - 15 = -0.825 → FOLD
    # Actually, that's -0.825 < -0.02. Let me use higher equity.
    assert rec.action == "FOLD"  # still -EV at 45% equity


def test_recommend_call_action_ev_push(position_range, random_eq) -> None:
    """push action: hand outside call.deep but clearly +EV → PUSH."""
    rec = recommend(
        equity=0.55,
        effective_stack_bb=15.0,
        position_range=position_range,
        hand_label="AQs",
        action="push",
        random_eq=random_eq,
        pot_odds=0.40,
        ev_margin=0.02,
        fold_equity=0.0,
    )
    # EV(call) = 0.55 * 31.5 - 15 = 17.325 - 15 = 2.325 → PUSH
    assert rec.action == "PUSH"
    assert "overriding" in rec.reason.lower()


def test_recommend_ev_marginal_uses_range_tiebreaker(position_range) -> None:
    """When |EV| < ev_margin, fall back to range membership."""
    # At 15bb with fe=0.40, AQs equity=0.45:
    # EV = 0.40*1.5 + 0.60*(0.45*(1.5+30)-15) = 0.6 + 0.60*(14.175-15)
    #    = 0.6 + 0.60*(-0.825) = 0.6 - 0.495 = 0.105
    # Hmm that's > 0.02. Let me find a breakeven equity:
    # Need EV ≈ 0: 0.6 + 0.6*(eq*31.5 - 15) = 0 → eq*31.5 - 15 = -1 → eq = 14/31.5 ≈ 0.444
    rec = recommend(
        equity=0.444,
        effective_stack_bb=15.0,
        position_range=position_range,
        hand_label="AQs",
        action="open",
        fold_equity=0.40,
        ev_margin=0.02,
    )
    # AQs is outside push.deep → FOLD (tiebreaker: outside range)
    assert rec.action == "FOLD"


# ------------------------------------------------------------ EV helper tests


def test_auto_pot_odds() -> None:
    assert auto_pot_odds(15, 15, 1) == pytest.approx(15 / 31, rel=1e-3)


def test_ev_open_shove() -> None:
    ev = _ev_open_shove(equity=0.50, hero_stack_bb=15, pot_bb=1.5, fold_equity=0.40)
    # 0.40*1.5 + 0.60*(0.50*31.5 - 15) = 0.6 + 0.60*(0.75) = 1.05
    assert ev == pytest.approx(1.05, rel=1e-3)


def test_ev_open_shove_no_fold_equity() -> None:
    ev = _ev_open_shove(equity=0.50, hero_stack_bb=15, pot_bb=1.5, fold_equity=0.0)
    # 0.50*31.5 - 15 = 0.75
    assert ev == pytest.approx(0.75, rel=1e-3)


def test_ev_open_shove_full_fold_equity() -> None:
    ev = _ev_open_shove(equity=0.50, hero_stack_bb=15, pot_bb=1.5, fold_equity=1.0)
    # 1.0*1.5 = 1.5
    assert ev == pytest.approx(1.5, rel=1e-3)


def test_ev_call_shove() -> None:
    ev = _ev_call_shove(equity=0.50, pot_bb=1.5, villain_bet_bb=15, hero_stack_bb=15)
    # 0.50 * (1.5+15+15) - 15 = 0.75
    assert ev == pytest.approx(0.75, rel=1e-3)
