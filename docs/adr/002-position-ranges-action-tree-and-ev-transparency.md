# ADR 002: Position-based hero ranges, action-aware decision tree, and EV transparency

## Status

Accepted

## Context

The first version of `strategy.py` used a single global `ShortStackConfig`
(one `deep_range` and one `wide_range`) regardless of hero position. In
practice, 3-max short-stack play needs materially different push ranges for
BTN, SB and BB:

- **BTN**: acts first with two players behind, so it shoves tighter.
- **SB**: only the big blind is left to act, so it can shove wider.
- **BB**: closes the action and mostly decides whether to call.

A second problem is that the opponent does not always shove; they may raise
2–3 bb or limp. The tool must distinguish "I was shoved on" (I need a
*call* range) from "I am opening or answering a non-all-in raise" (I need a
*push* range).

Finally, the recommendation was purely based on range membership. After
range interpolation was introduced, `equity_vs_villain_range` and pot odds
were no longer visible, and the user could not see *why* a given
recommendation was produced.

## Decision

### 1. Position-based hero ranges in config

The global `short_stack` block is replaced by `hero_ranges` keyed by position.
Each position has a push and a call range, each in a deep and a wide version
(excerpt of the defaults):

```yaml
hero_ranges:
  BTN:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    interpolation_curve: threshold
    tight_until_pct: 0.85
    push:
      deep: "22+, A2s+, A2o+, K2s+, KTo+, Q9s+, QTo+, JTs, T9s, 98s, 87s, 76s, 65s"
      wide: "22+, A2s+, A2o+, K2s+, K2o+, Q2s+, Q2o+, J2s+, J2o+, T2s+, T7o+, 97s+, 87s, 76s, 65s, 54s"
    call:
      deep: "22+, A9s+, AJo+, KQs"
      wide: "22+, A2s+, A2o+, K2s+, KJo+, QTs+"
```

**Data model:**

```python
@dataclass
class RangePair:
    deep: str
    wide: str


@dataclass
class PositionRangeConfig:
    deep_stack_bb: float
    short_stack_bb: float
    desperation_bb: float
    interpolation_curve: str = "threshold"   # ADR 004
    tight_until_pct: float = 0.85
    push: RangePair = field(default_factory=lambda: RangePair("", ""))
    call: RangePair = field(default_factory=lambda: RangePair("", ""))
```

`RangetoolConfig.get_hero_range_config(position)` returns the config for the
current hero seat. On load, every call range must be a subset of the push range
at the same depth.

### 2. Action-aware decision tree (MVP: push vs non-push)

The `hand` REPL command takes an optional action argument:

```text
hand AKs          # hero acts first / open (default)
hand AKs push     # opponent shoved
hand AKs raise    # opponent made a non-all-in raise
hand AKs limp     # opponent limped
```

| Opponent action | Hero range used | Meaning |
|-----------------|-----------------|---------|
| `push` (all-in) | `call` range, interpolated | "Should I call the shove?" |
| `raise` (not all-in) | `push` range, interpolated | "Can I reshove over the raise?" |
| `limp` | `push` range, interpolated | "Can I push over the limp?" |
| `open` | `push` range, interpolated | "I open-shove." |

For `push`, the opponent is assumed to have shoved the full effective stack S,
so the required equity is `S / (1.5 + 2S)`. `raise` and `limp` are evaluated
like an open shove into the 1.5 bb of blinds; the extra chips of the raise or
limp are not modelled yet. `strategy.auto_pot_odds()` computes the required
equity for arbitrary bet sizes and is the building block for that.

### 3. EV-first decision logic

Pure range membership is replaced with an EV check in bb:

```python
if action == "push":                       # calling a shove, no fold equity
    ev = equity * (pot + 2 * stack) - stack
else:                                      # open / raise / limp: hero shoves
    ev = fe * pot + (1 - fe) * (equity * (pot + 2 * stack) - stack)

if ev >= ev_margin:
    return PUSH          # reason says whether it overrides the configured range
if ev < -ev_margin:
    return FOLD          # reason says whether the hand was inside the range
return PUSH if hand in hero_range else FOLD   # marginal: range breaks the tie
```

`pot` is 1.5 bb, `fe` is the configured fold equity (default 0.40) and
`ev_margin` defaults to 0.02 bb. The margin prevents razor-thin edges from
flipping the verdict. When the stack is unknown, the decision falls back to
range membership.

### 4. Transparent output

The `hand` command prints every input to the decision:

```text
(BTN|15.0bb) > hand A5s push
A5s (4 combos)
  Hero position: BTN
  Action: push (villain shoved; hero decides whether to call)
  Villain range: 49 hands
  Equity vs villain range: 45.26%
  Effective stack: 15.0bb
  Pot: 1.5 bb  |  Villain bet: 15.0 bb  |  Hero risk: 15.0 bb
  Required equity (pot odds): 47.62%
  EV of calling: -0.74 bb
  Range for this spot: 22 hands
  Recommendation: FOLD
  Reason: A5s: -EV (-0.74bb) and not in the 22-hand call range
```

## Consequences

### Positive

- Recommendations depend on position.
- The tool distinguishes "I am calling a shove" from "I am shoving".
- The user sees the full math (equity, pot odds, EV), so every verdict can be
  checked by hand.
- The EV check catches +EV shoves that an overly tight configured range would
  miss, and -EV shoves that an overly loose one would allow.

### Negative / risks

- Configuration grows: 12 range strings (push/call × deep/wide × 3 positions)
  instead of 2.
- `ev_margin` and `fold_equity` are extra tuning parameters, and a single
  fixed fold equity is a coarse model.
- Raise and limp sizes are not yet part of the EV calculation.

## Alternatives considered

1. **Keep one global range with positional modifiers (±N hands).** Rejected:
   less transparent than explicit positional ranges.
2. **Full decision tree (push / raise 2x / raise 3x / limp with separate
   ranges for each).** Deferred: push vs non-push covers most spots at these
   stack depths.
3. **Pure EV-based approach without ranges.** Rejected: ranges encode the
   user's strategy and preferences and act as the tie-breaker.

## Related

- ADR 001 (session-based CLI)
- ADR 004 (non-linear interpolation applies to each configured range)
- `rangetool/config.py`, `rangetool/strategy.py`, `rangetool/repl.py`
