# ADR 002: Position-based hero ranges, action-aware decision tree, and EV transparency

## Status

Proposed

## Context

The current `strategy.py` operates on a single global `ShortStackConfig` (one
`deep_range` / one `wide_range`) regardless of hero position. In practice,
JAQKpot play requires materially different push ranges for BTN, SB and BB:

- **BTN** — around top-15% GTO (acts first, can steal).
- **SB** — around top-12% (caught between BTN and BB).
- **BB** — around top-25% (closes the action, can call wider).

A second problem is that the opponent does not always shove; they may raise
2–3 bb or limp. The tool must distinguish "I was shoved on" (I need a
*call* range) from "I am opening/answering a non-all-in raise" (I need a
*push* range).

Finally, the recommendation is currently purely range-membership based. After
range interpolation was introduced, `equity_vs_villain_range` and `pot_odds`
became invisible and secondary. The user cannot see *why* a given
recommendation was produced.

## Decision

### 1. Position-based hero ranges in config

The global `short_stack` block is replaced by `hero_ranges` keyed by position:

```yaml
hero_ranges:
  BTN:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    push:
      deep: "22+, A5s+, A8o+, KTs+, KJo+, QJs, JTs, T9s"
      wide: "22+, Axo, Axs, K4s+, K8o+, Q8s+, QTo+, J9s+, T8s+, 98s"
    call:
      deep: "44+, A9s+, AJo+, KQs"
      wide: "22+, Axo, Axs, K6s+, KTo+, Q8s+, QTo+"
  SB:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    push:
      deep: "33+, A8s+, AJo+, KJs+, KQo, QJs"
      wide: "22+, Axo, Axs, K5s+, K9o+, Q8s+, QTo+, J9s+, T8s+, 98s"
    call:
      deep: "55+, ATs+, AQo+, JJ+"
      wide: "22+, A5s+, A9o+, KTs+, KQo, QJs"
  BB:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    push:
      deep: "22+, Axo, Axs, Kxs+, Q8s+, QTo+, JTs+"
      wide: "22+, Axo, Axs, Kxo, Qxs, Jxs, T8o+, 54s+"
    call:
      deep: "22+, A2s+, A8o+, KTs+, KJo+, QJs"
      wide: "22+, Axo, Axs, Kxs+, QTs+, JTs"
```

**Data model:**

```python
@dataclass
class PositionRangeConfig:
    deep_stack_bb: float
    short_stack_bb: float
    desperation_bb: float
    push: RangePair
    call: RangePair


@dataclass
class RangePair:
    deep: str
    wide: str
```

`Session.get_hero_range()` selects the correct `PositionRangeConfig` based on
current `hero_position`.

### 2. Action-aware decision tree (MVP: push vs non-push)

The `hand` REPL command gets an optional action argument:

```text
hand AKs          # hero acts first / open (default)
hand AKs push     # opponent shoved
hand AKs raise    # opponent made a non-all-in raise
hand AKs limp     # opponent limped
```

**Recommendation mapping:**

| Opponent action | Hero range used | Meaning |
|-----------------|-----------------|---------|
| `push` (all-in) | `call_range` interpolated | "Should I call the shove?" |
| `raise` (not all-in) | `push_range` interpolated | "Can I reshove over the raise?" |
| `limp` | `push_range` interpolated | "Can I push over the limp?" |
| `open` | `push_range` interpolated | "I open shove." |

`auto_pot_odds()` is recomputed for the action: if opponent bets 2 bb into a
1.5 bb pot and the effective stack is 12 bb, the required equity is
`12 / (12 + 2 + 1.5)`.

### 3. EV-first decision logic

Pure range-membership logic is replaced with an EV check:

```python
def recommend(equity, pot_odds, hand_label, hero_range, ev_margin=0.02):
    in_range = hand_label in hero_range

    if equity >= pot_odds + ev_margin:
        if in_range:
            return PUSH(reason="+EV and inside configured range")
        return PUSH(reason=f"+EV ({equity:.1%} > {pot_odds:.1%}), overriding conservative range")

    if in_range:
        return FOLD(reason=f"inside range but -EV: equity {equity:.1%} < pot odds {pot_odds:.1%}")
    return FOLD(reason=f"-EV and outside range")
```

`ev_margin` defaults to 0.02 (2%). It prevents recommending a push on a
razor-thin edge where variance dominates.

### 4. Transparent output

The `hand` command output becomes:

```text
> hand AKs push
Villain action: push
Villain range: 22+, Axo, Axs, Kxs+, Qxs+, JTs+ (94 hands)
AKs (4 combos) equity vs villain range: 67.3%
Pot: 16.5 bb  |  Villain bet: 14.0 bb  |  Hero risk: 14.0 bb
Required equity (pot odds): 45.2%
EV push: +3.1 bb  |  EV fold: 0.0 bb
Range for this spot: 84 hands (interpolated at 14.0 bb)
AKs is in range: YES
─────────────────────────────────────────
RECOMMENDATION: PUSH  (+EV, in range)
```

## Consequences

### Positive

- Recommendations become positionally accurate.
- Tool distinguishes "I am calling a shove" from "I am shoving".
- The user sees the full math: equity, pot odds, EV — the decision is
  transparent.
- EV-based fallback prevents missing +EV pushes because of an overly tight
  configured range.

### Negative / risks

- Configuration grows: 6 ranges (push/call × 3 positions) instead of 2.
- `ev_margin` is another tuning parameter.
- `auto_pot_odds` must know opponent action and bet size, requiring more
  session input.

## Alternatives considered

1. **Keep one global range with positional modifiers (±N hands).** Rejected:
   less transparent than explicit positional ranges.
2. **Full decision tree (push / raise 2x / raise 3x / limp with separate
   ranges for each).** Deferred: MVP push-vs-non-push covers ~80% of JAQKpot
   spots.
3. **Pure EV-based approach without ranges.** Rejected: ranges encode user
   strategy/preferences and should remain the primary filter.

## Related

- ADR 001 (session-based CLI)
- ADR 004 (non-linear interpolation applies to each of the 6 ranges)
- `rangetool/config.py`, `rangetool/strategy.py`, `rangetool/repl.py`
