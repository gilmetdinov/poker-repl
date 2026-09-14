# ADR 003: Blind deduction on rotation and blind schedule rework

## Status

Proposed

## Context

Two related problems exist in `session.py`:

1. **Blinds are not deducted on rotation.** `next_hand()` advances position but
   leaves `effective_stack_bb` unchanged. The user must manually run
   `stack N-1.5` after every orbit. In real JAQKpot play each hand costs
   something: SB pays 0.5 bb, BB pays 1 bb, BTN pays nothing.

2. **The blind schedule model is wrong.** The current `BlindLevel` stores
   `small_blind`/`big_blind` as absolute chip values (5/10, 10/20, ...) and
   computes effective stack as `starting_stack_bb * 10 / bb`. This does not
   match tournament mechanics: in JAQKpot you start with 15 bb (300 chips when
   bb = 20), and when blinds move to bb = 30 your stack in bb becomes
   300 / 30 = 10 bb. The formula `15 * 10 / 30 = 5 bb` is incorrect. The
   session should store stack in bb as the primary value and recompute it on
   level change using the ratio of big-blind chip values.

## Decision

### 1. Auto blind deduction in `next_hand()`

`Session.next_hand()` subtracts the blind cost before rotating:

```python
def next_hand(self) -> str:
    if self.effective_stack_bb is not None:
        cost = _blind_cost_for_position(self.hero_position)
        self.effective_stack_bb = max(0.1, self.effective_stack_bb - cost)
    # existing rotation logic follows
```

| Position | Cost   |
|----------|--------|
| SB       | 0.5 bb |
| BB       | 1.0 bb |
| BTN      | 0 bb   |

The deduction is always in bb, independent of blind level.

### 2. Blind schedule rework: chip-value model

**New `BlindLevel` model:**

```python
@dataclass
class BlindLevel:
    level: int
    bb_chips: int       # chip value of one big blind
    duration_min: int
    # small blind is derived as bb_chips / 2
```

**New session logic:**

- `effective_stack_bb` is the **primary value**, always in bb. It is
  initialized from `starting_stack_bb`.
- On level change (`set_level(n)` or `set_level_by_time(t)`) recompute:

```python
def _recompute_stack_for_level(
    self, old_bb_chips: int, new_bb_chips: int
) -> None:
    if self.effective_stack_bb is None:
        return
    ratio = old_bb_chips / new_bb_chips
    self.effective_stack_bb = round(self.effective_stack_bb * ratio, 2)
```

- The user can still override the stack with `stack <bb>`.

**New config example:**

```yaml
blind_schedule:
  - level: 1
    bb_chips: 10
    duration_min: 5
  - level: 2
    bb_chips: 20
    duration_min: 5
  - level: 3
    bb_chips: 30
    duration_min: 5
  - level: 4
    bb_chips: 50
    duration_min: 5
  - level: 5
    bb_chips: 80
    duration_min: 5
```

**Example:** Starting stack 15 bb. Level 1 (bb = 10 chips), level 2
(bb = 20 chips). On level change: `15 * (10 / 20) = 7.5 bb`.

### 3. Migration path

Old configs containing `small_blind`/`big_blind` are auto-migrated on load:
- Warn the user that the old format is deprecated.
- Convert to `bb_chips = big_blind`.
- `starting_stack_bb` remains as the initial value.

## Consequences

### Positive

- Stack is automatically tracked between hands; no manual fix-up after every
  orbit.
- Level model matches real tournament mechanics: a level changes the chip
  price of a bb, it does not magically shrink the stack.
- `bb_chips` makes `blind_schedule` more readable (5 numbers instead of 10).

### Negative / risks

- Breaks config backward compatibility (mitigated by auto-migration).
- BB deduction (1 bb) on a very short stack (< 2 bb) can push the stack below
  0.1 bb; clamp to a minimum (0.1 bb or `desperation_bb`).
- User must understand the difference between "stack in bb" and "stack in
  chips".

## Alternatives considered

1. **Do not auto-deduct blinds; keep manual entry.** Rejected: it was the main
   complaint in the recap.
2. **Store stack in chips and compute bb on the fly.** Rejected: the user
   thinks in bb, and all ranges and thresholds are expressed in bb.
3. **Deduct blinds after rotation instead of before.** Rejected: blinds are
   posted *before* the hand, so the deduction belongs before rotation.

## Related

- ADR 001 (session REPL design)
- ADR 002 (position-based ranges are affected by stack tracking)
- `rangetool/session.py`, `rangetool/config.py`, `rangetool/config.yaml`
