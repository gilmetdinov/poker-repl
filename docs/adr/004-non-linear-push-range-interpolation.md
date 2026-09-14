# ADR 004: Non-linear push-range interpolation

## Status

Proposed

## Context

The current `_interpolated_push_range()` uses a linear blend between
`deep_range` (at 15 bb) and `wide_range` (at 2 bb). This means that dropping
from 15 bb to 14 bb already adds roughly 8% of the extra hands (`wide - deep`).
In practice this is too aggressive: a player should not widen the push range
sharply after a small loss of stack. Up to a certain threshold (around
12–13 bb) the range should stay almost unchanged, and only after that point
should widening accelerate.

## Decision

### 1. Configuration parameter

Add a curve selector to `PositionRangeConfig` (or the legacy `ShortStackConfig`):

```python
interpolation_curve: str = "threshold"  # "linear" | "threshold" | "sigmoid"
tight_until_pct: float = 0.85            # active when curve == "threshold"
```

Config example:

```yaml
hero_ranges:
  BTN:
    deep_stack_bb: 15.0
    short_stack_bb: 2.0
    desperation_bb: 0.5
    interpolation_curve: threshold
    tight_until_pct: 0.85
    push:
      deep: "22+, A5s+, A8o+, KTs+, KJo+, QJs, JTs, T9s"
      wide: "22+, Axo, Axs, K4s+, K8o+, Q8s+, QTo+, J9s+, T8s+, 98s"
```

### 2. Implementation: threshold mode

```python
def _interpolated_push_range(stack_bb, config, random_eq):
    deep = parse_range(config.deep)
    wide = parse_range(config.wide)

    if stack_bb is None or stack_bb >= config.deep_stack_bb:
        return deep
    if stack_bb <= config.short_stack_bb:
        return wide

    if config.interpolation_curve == "threshold":
        tight_limit = config.deep_stack_bb * config.tight_until_pct
        if stack_bb >= tight_limit:
            return deep

        # Below the threshold, interpolate linearly down to wide_range.
        # alpha = 1 at tight_limit, alpha = 0 at short_stack_bb.
        alpha = (stack_bb - config.short_stack_bb) / (
            tight_limit - config.short_stack_bb
        )
        extra = wide - deep
        quality = _hand_quality_key(random_eq)
        ordered_extra = sorted(extra, key=quality, reverse=True)
        fraction = 1.0 - alpha
        count = int(fraction * len(ordered_extra))
        return deep | set(ordered_extra[:count])

    if config.interpolation_curve == "sigmoid":
        # Reserved for future implementation; see spec below.
        ...

    # Default "linear" — preserve current behavior.
    alpha = (stack_bb - config.short_stack_bb) / (
        config.deep_stack_bb - config.short_stack_bb
    )
    ...
```

### 3. Sigmoid mode (future spec)

For sigmoid mode, transform the linear `alpha` through a sigmoid centered at
the midpoint of the interval with configurable steepness:

```python
raw_alpha = (stack_bb - short_stack_bb) / (deep_stack_bb - short_stack_bb)
midpoint = 0.5
sigmoid_alpha = 1 / (1 + math.exp(-steepness * (raw_alpha - midpoint)))
```

Sigmoid gives a near-flat plateau at high stacks, a rapid transition in the
middle, and a flat plateau at low stacks. It is harder to explain than
threshold mode, so threshold is the recommended default.

## Consequences

### Positive

- Range does not widen prematurely on a small stack loss.
- The user controls interpolation aggressiveness with one intuitive parameter,
  `tight_until_pct`.
- Threshold model is easy to communicate: "keep the deep range until 85% of the
  starting stack, then widen".

### Negative / risks

- Adds 1–2 parameters per position in the config.
- At `tight_until_pct = 1.0` the behavior collapses to no interpolation
  between deep and wide, which may confuse users.
- Sigmoid requires tuning a `steepness` parameter; left as future work.

## Alternatives considered

1. **Step-wise interpolation at fixed stack points.** Rejected: more
   parameters without added flexibility over threshold mode.
2. **Exponential interpolation.** Rejected: mathematically similar to a
   sigmoid but less intuitive.
3. **Keep only linear interpolation.** Rejected: the recap explicitly calls
   out that the range widens too quickly at high stacks.

## Related

- ADR 002 (position-based ranges — interpolation applies to each of the 6
  configured ranges)
- `rangetool/strategy.py:_interpolated_push_range()`
