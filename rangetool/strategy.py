"""Action recommendation logic for the session REPL."""

from __future__ import annotations

import math
from dataclasses import dataclass

from rangetool.config import PositionRangeConfig, RangePair
from rangetool.hands import ALL_HAND_LABELS
from rangetool.range_parser import parse_range


@dataclass
class Recommendation:
    """A strategy recommendation for a given hand in a given spot."""

    action: str
    equity: float
    pot_odds: float | None
    reason: str
    range_size: int | None = None
    ev_bb: float | None = None


# Actions where hero is the aggressor (open shove, reshove over a raise/limp).
_AGGRESSOR_ACTIONS = {"open", "raise", "limp"}
# Actions where hero faces an all-in and decides whether to call.
_REACTIVE_ACTIONS = {"push"}

VALID_ACTIONS = _AGGRESSOR_ACTIONS | _REACTIVE_ACTIONS


def recommend(
    equity: float,
    effective_stack_bb: float | None,
    position_range: PositionRangeConfig,
    hand_label: str,
    action: str = "open",
    random_eq: dict[str, float] | None = None,
    pot_odds: float | None = None,
    ev_margin: float = 0.02,
    fold_equity: float = 0.40,
) -> Recommendation:
    """Return a push/fold recommendation using EV-first logic for all actions.

    The configured range acts as a conservative baseline: EV can override it
    in either direction.  For aggressor actions (open / raise / limp) fold
    equity is factored into the EV calculation.

    Args:
        equity: Equity of the hero hand vs the villain range (0..1).
        effective_stack_bb: Current effective stack in bb, or None.
        position_range: Position-specific push/call ranges and interpolation.
        hand_label: Hero hand label (e.g. "AKs").
        action: Situation: open, push, raise, limp.
        random_eq: Optional equity-vs-random map for interpolation ordering.
        pot_odds: Required equity to break even on a call (only for ``push``).
        ev_margin: Minimum +EV threshold in bb before recommending a push.
        fold_equity: Probability villain folds to an open-shove (0..1).

    Returns:
        A Recommendation.
    """
    action = action.lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f"unknown action: {action!r}")

    stack = effective_stack_bb

    # Desperation: push any two cards.
    if stack is not None and stack <= position_range.desperation_bb:
        return Recommendation(
            action="PUSH",
            equity=equity,
            pot_odds=pot_odds,
            reason=f"effective stack {stack:.1f}bb: desperation push",
            range_size=169,
        )

    # Select the appropriate hero range: push for aggressor, call for reactive.
    is_aggressor = action in _AGGRESSOR_ACTIONS
    range_pair = position_range.push if is_aggressor else position_range.call
    hero_range = _interpolated_range(stack, position_range, range_pair, random_eq)
    in_range = hand_label in hero_range

    # --- Compute EV of the action -------------------------------------------
    pot = 1.5  # blinds (SB 0.5 + BB 1.0)
    ev = None
    if stack is not None:
        if is_aggressor:
            ev = _ev_open_shove(equity, stack, pot, fold_equity)
        elif pot_odds is not None:
            # Facing a shove: villain shoved their stack.
            ev = _ev_call_shove(equity, pot, stack, stack)

    # --- Decision ------------------------------------------------------------
    if ev is None:
        # No stack info → fall back to range-only decision.
        return _range_only_recommendation(
            hand_label, equity, pot_odds, in_range, hero_range,
            stack, position_range, action,
        )

    range_info = f" ({len(hero_range)}-hand {action} range)"

    if ev >= ev_margin:
        if in_range:
            return Recommendation(
                action="PUSH",
                equity=equity,
                pot_odds=pot_odds,
                reason=(
                    f"{hand_label} EV {ev:+.2f}bb (+EV, in range{range_info})"
                ),
                range_size=len(hero_range),
                ev_bb=ev,
            )
        return Recommendation(
            action="PUSH",
            equity=equity,
            pot_odds=pot_odds,
            reason=(
                f"{hand_label} EV {ev:+.2f}bb: +EV shove, overriding conservative"
                f"{range_info}"
            ),
            range_size=len(hero_range),
            ev_bb=ev,
        )

    if ev < -ev_margin:
        if in_range:
            return Recommendation(
                action="FOLD",
                equity=equity,
                pot_odds=pot_odds,
                reason=(
                    f"{hand_label} EV {ev:+.2f}bb: -EV despite being in"
                    f"{range_info}"
                ),
                range_size=len(hero_range),
                ev_bb=ev,
            )
        return Recommendation(
            action="FOLD",
            equity=equity,
            pot_odds=pot_odds,
            reason=(
                f"{hand_label} EV {ev:+.2f}bb: -EV fold, outside{range_info}"
            ),
            range_size=len(hero_range),
            ev_bb=ev,
        )

    # Marginal case (|ev| < ev_margin): use range as tiebreaker.
    if in_range:
        return Recommendation(
            action="PUSH",
            equity=equity,
            pot_odds=pot_odds,
            reason=(
                f"{hand_label} EV {ev:+.2f}bb (marginal, in range{range_info})"
            ),
            range_size=len(hero_range),
            ev_bb=ev,
        )
    return Recommendation(
        action="FOLD",
        equity=equity,
        pot_odds=pot_odds,
        reason=(
            f"{hand_label} EV {ev:+.2f}bb (marginal, outside{range_info})"
        ),
        range_size=len(hero_range),
        ev_bb=ev,
    )


def _range_only_recommendation(
    hand_label: str,
    equity: float,
    pot_odds: float | None,
    in_range: bool,
    hero_range: set[str],
    stack: float | None,
    position_range: PositionRangeConfig,
    action: str,
) -> Recommendation:
    """Fallback recommendation when EV cannot be computed (no stack info)."""
    if in_range:
        return Recommendation(
            action="PUSH",
            equity=equity,
            pot_odds=pot_odds,
            reason=_range_reason(hand_label, stack, hero_range, position_range, action, True),
            range_size=len(hero_range),
        )
    return Recommendation(
        action="FOLD",
        equity=equity,
        pot_odds=pot_odds,
        reason=_range_reason(hand_label, stack, hero_range, position_range, action, False),
        range_size=len(hero_range),
    )


def _ev_open_shove(
    equity: float,
    hero_stack_bb: float,
    pot_bb: float,
    fold_equity: float,
) -> float:
    """Return the EV of an open-shove, accounting for fold equity.

    Args:
        equity: Hero hand equity against the villain's calling range.
        hero_stack_bb: Effective stack the hero risks.
        pot_bb: Current pot (blinds + any prior bets).
        fold_equity: Probability all opponents fold (0..1).

    Returns:
        Expected value in bb relative to folding.
    """
    fe = max(0.0, min(1.0, fold_equity))
    pot_if_called = pot_bb + 2 * hero_stack_bb
    ev_when_called = equity * pot_if_called - hero_stack_bb
    return fe * pot_bb + (1.0 - fe) * ev_when_called


def _ev_call_shove(
    equity: float,
    pot_bb: float,
    villain_bet_bb: float,
    hero_stack_bb: float,
) -> float:
    """Return the EV of calling a shove (no fold equity).

    Args:
        equity: Hero hand equity against the villain's shoving range.
        pot_bb: Pot before villain's bet.
        villain_bet_bb: Villain's all-in amount.
        hero_stack_bb: Amount the hero risks (typically = villain_bet_bb).

    Returns:
        Expected value in bb relative to folding.
    """
    total_pot = pot_bb + villain_bet_bb + hero_stack_bb
    return equity * total_pot - hero_stack_bb


def _interpolated_range(
    stack_bb: float | None,
    position_range: PositionRangeConfig,
    range_pair: RangePair,
    random_eq: dict[str, float] | None,
) -> set[str]:
    """Return the interpolated hero range for a given stack and range pair."""
    deep = parse_range(range_pair.deep)
    wide = parse_range(range_pair.wide)

    deep_stack = position_range.deep_stack_bb
    short_stack = position_range.short_stack_bb

    if stack_bb is None or stack_bb >= deep_stack:
        return deep
    if stack_bb <= short_stack:
        return wide

    extra = wide - deep
    if not extra:
        return deep

    quality = _hand_quality_key(random_eq)
    ordered_extra = sorted(extra, key=quality, reverse=True)
    curve = position_range.interpolation_curve

    if curve == "threshold":
        tight_limit = deep_stack * position_range.tight_until_pct
        if stack_bb >= tight_limit:
            return deep
        fraction = 1.0 - (stack_bb - short_stack) / (tight_limit - short_stack)
    elif curve == "sigmoid":
        fraction = _sigmoid_fraction(stack_bb, deep_stack, short_stack)
    else:  # "linear"
        fraction = 1.0 - (stack_bb - short_stack) / (deep_stack - short_stack)

    fraction = max(0.0, min(1.0, fraction))
    count = int(fraction * len(ordered_extra))
    return deep | set(ordered_extra[:count])


def _sigmoid_fraction(stack_bb: float, deep_stack: float, short_stack: float) -> float:
    """Return the fraction of extra hands to add using a sigmoid curve."""
    raw = (stack_bb - short_stack) / (deep_stack - short_stack)
    # Center the transition in the middle of the interval; steepness = 6 gives
    # a reasonably sharp but smooth transition.
    steepness = 6.0
    midpoint = 0.5
    sigmoid = 1.0 / (1.0 + math.exp(-steepness * (raw - midpoint)))
    return 1.0 - sigmoid


def _hand_quality_key(random_eq: dict[str, float] | None):
    """Return a sort key for hand labels used when interpolating ranges."""
    if random_eq:
        return lambda label: random_eq.get(label, 0.0)
    # Deterministic fallback: canonical 169-hand order.
    order = {label: idx for idx, label in enumerate(ALL_HAND_LABELS)}
    return lambda label: -order.get(label, 0)


def _range_reason(
    hand_label: str,
    stack_bb: float | None,
    hero_range: set[str],
    position_range: PositionRangeConfig,
    action: str,
    in_range: bool,
) -> str:
    parts = [
        f"{hand_label} {'is' if in_range else 'is not'} in {len(hero_range)}-hand {action} range"
    ]
    if stack_bb is not None:
        parts.append(f"at {stack_bb:.1f}bb effective")
        if position_range.short_stack_bb < stack_bb < position_range.deep_stack_bb:
            parts.append(f"({position_range.interpolation_curve} interpolated)")
    return " ".join(parts)


def auto_pot_odds(hero_stack_bb: float, villain_bet_bb: float, pot_bb: float) -> float:
    """Return the required equity to call or reshove.

    Args:
        hero_stack_bb: Amount the hero must risk.
        villain_bet_bb: Villain's bet/all-in size.
        pot_bb: Current pot before the hero's call.

    Returns:
        Required equity as a float 0..1.
    """
    total_pot_after_call = pot_bb + villain_bet_bb + hero_stack_bb
    return hero_stack_bb / total_pot_after_call if total_pot_after_call else 0.0


def ev_push(
    equity: float,
    hero_stack_bb: float,
    villain_bet_bb: float,
    pot_bb: float,
) -> float:
    """Return the EV of a call/reshove in bb assuming we are always called.

    This is a conservative model that ignores fold equity; it is appropriate
    for comparing push vs fold when facing an all-in or a raise we intend to
    reshove over.

    Args:
        equity: Hero equity against the villain range.
        hero_stack_bb: Amount hero risks.
        villain_bet_bb: Villain's bet/all-in size.
        pot_bb: Pot before villain's bet.

    Returns:
        Expected value in bb relative to folding.
    """
    total_pot = pot_bb + villain_bet_bb + hero_stack_bb
    return equity * total_pot - hero_stack_bb
