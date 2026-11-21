# ADR 004: Non-linear push-range interpolation

## Status

Accepted

## Context

Hero ranges are interpolated between a `deep` range (at `deep_stack_bb`,
15 bb by default) and a `wide` range (at `short_stack_bb`, 2 bb). The extra
hands (`wide - deep`) are sorted by equity against a random hand, and the
strongest fraction of them is added as the stack shrinks.

A linear blend means that dropping from 15 bb to 14 bb already adds roughly
8% of the extra hands. That is too aggressive: a small loss of stack should
not widen the push range noticeably. Down to a threshold (around 12–13 bb)
the range should stay unchanged, and only below that should it widen.

## Decision

### 1. Configuration parameter

Each `PositionRangeConfig` gets a curve selector:

```python
interpolation_curve: str = "threshold"  # "linear" | "threshold" | "sigmoid"
tight_until_pct: float = 0.85            # used when curve == "threshold"
```

```yaml
hero_ranges:
  BTN:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    interpolation_curve: threshold
    tight_until_pct: 0.85
```

### 2. Implementation

`strategy._interpolated_range()` applies the curve to each push/call range
pair:

```python
deep, wide = parse_range(pair.deep), parse_range(pair.wide)
if stack_bb is None or stack_bb >= deep_stack_bb:
    return deep
if stack_bb <= short_stack_bb:
    return wide

ordered_extra = sorted(wide - deep, key=equity_vs_random, reverse=True)

if curve == "threshold":
    tight_limit = deep_stack_bb * tight_until_pct
    if stack_bb >= tight_limit:
        return deep
    fraction = 1 - (stack_bb - short_stack_bb) / (tight_limit - short_stack_bb)
elif curve == "sigmoid":
    fraction = sigmoid_fraction(stack_bb, deep_stack_bb, short_stack_bb)
else:  # "linear"
    fraction = 1 - (stack_bb - short_stack_bb) / (deep_stack_bb - short_stack_bb)

return deep | set(ordered_extra[: int(fraction * len(ordered_extra))])
```

### 3. Sigmoid mode

Sigmoid mode transforms the linear position through a logistic curve centred
on the middle of the interval, with a fixed steepness of 6:

```python
raw = (stack_bb - short_stack_bb) / (deep_stack_bb - short_stack_bb)
fraction = 1 - 1 / (1 + math.exp(-6 * (raw - 0.5)))
```

It gives a near-flat plateau at high stacks, a fast transition in the middle
and another plateau at low stacks. It is harder to explain than threshold
mode, so threshold is the default.

## Consequences

### Positive

- The range does not widen prematurely after a small loss of stack.
- One intuitive parameter, `tight_until_pct`, controls how aggressive the
  interpolation is.
- The threshold model is easy to explain: "keep the deep range until 85% of
  the starting stack, then widen".

### Negative / risks

- One or two more parameters per position in the config.
- At `tight_until_pct = 1.0` threshold mode behaves like linear mode over the
  whole interval, which may surprise users.
- Sigmoid steepness is fixed in code, not configurable.

## Alternatives considered

1. **Step-wise interpolation at fixed stack points.** Rejected: more
   parameters without more flexibility than threshold mode.
2. **Exponential interpolation.** Rejected: similar to a sigmoid but less
   intuitive.
3. **Keep only linear interpolation.** Rejected: it widens the range too
   quickly at high stacks.

## Related

- ADR 002 (position-based ranges; interpolation applies to each configured
  range)
- `rangetool/strategy.py:_interpolated_range()`
