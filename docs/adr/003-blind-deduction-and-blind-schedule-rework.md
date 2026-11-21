# ADR 003: Blind deduction on rotation and blind schedule rework

## Status

Accepted

## Context

Two related problems existed in `session.py`:

1. **Blinds were not deducted on rotation.** `next_hand()` advanced the
   position but left `effective_stack_bb` unchanged, so the user had to
   correct the stack by hand after every orbit. In a real tournament every
   hand in the blinds costs something: SB pays 0.5 bb, BB pays 1 bb, BTN pays
   nothing.

2. **The blind schedule model was wrong.** `BlindLevel` stored
   `small_blind`/`big_blind` as absolute chip values (5/10, 10/20, ...) and
   computed the effective stack as `starting_stack_bb * 10 / bb`. That does
   not match tournament mechanics: a 15 bb stack is 300 chips at bb = 20, and
   when the big blind moves to 30 the same 300 chips are 10 bb. The formula
   `15 * 10 / 30 = 5 bb` is incorrect. The session should store the stack in
   bb as the primary value and rescale it on a level change by the ratio of
   big-blind chip values.

## Decision

### 1. Automatic blind deduction in `next_hand()`

`Session.next_hand()` rotates the hero seat first and then deducts the blind
of the seat being entered, because that blind is posted for the hand that is
about to be played:

```python
def next_hand(self) -> str:
    rotation = ROTATION_HU if self.is_heads_up else ROTATION_3MAX
    idx = rotation.index(self.hero_position)
    self.hero_position = rotation[(idx + 1) % len(rotation)]
    if self.effective_stack_bb is not None:
        cost = _blind_cost_for_position(self.hero_position)
        self.effective_stack_bb = max(0.1, self.effective_stack_bb - cost)
    return self.hero_position
```

| Position entered | Cost   |
|------------------|--------|
| SB               | 0.5 bb |
| BB               | 1.0 bb |
| BTN              | 0 bb   |

The deduction is always in bb, independent of the blind level. The stack is
clamped at 0.1 bb so it never reaches zero.

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

**Session logic:**

- `effective_stack_bb` is the **primary value**, always in bb. It is
  initialized from `starting_stack_bb`.
- On a level change (`set_level(n)` or `set_level_by_time(t)`) the stack is
  rescaled:

```python
def _recompute_stack_for_new_level(self, new_level) -> None:
    old_bb = self.last_level_bb_chips
    new_bb = new_level.bb_chips
    if old_bb and new_bb and old_bb != new_bb:
        self.effective_stack_bb = round(self.effective_stack_bb * old_bb / new_bb, 2)
    self.last_level_bb_chips = new_bb
```

- The user can still override the stack with `stack <bb>`.

**Config example (the defaults):**

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

**Example:** starting stack 15 bb at level 1 (bb = 10 chips). Moving to
level 2 (bb = 20 chips) gives `15 * (10 / 20) = 7.5 bb`.

### 3. Migration path

Configs that still contain `small_blind`/`big_blind` are converted on load
(`bb_chips = big_blind`); `starting_stack_bb` keeps its meaning.

## Consequences

### Positive

- The stack is tracked between hands without manual corrections.
- The level model matches tournament mechanics: a level changes the chip
  price of a big blind, it does not shrink the stack by itself.
- `bb_chips` makes `blind_schedule` shorter (one number per level instead
  of two).

### Negative / risks

- The config format changed (mitigated by the automatic conversion).
- On a very short stack (< 1 bb) the BB deduction would go below zero; the
  0.1 bb clamp keeps the stack positive.
- The user has to keep "stack in bb" and "stack in chips" apart.

## Alternatives considered

1. **Do not auto-deduct blinds; keep manual entry.** Rejected: correcting the
   stack after every hand was the main source of input errors.
2. **Store the stack in chips and compute bb on the fly.** Rejected: the user
   thinks in bb, and all ranges and thresholds are expressed in bb.
3. **Charge the blind of the seat being left, before rotating.** Rejected:
   that bills the blind to the hand that has already been played instead of
   the one being entered.

## Related

- ADR 001 (session REPL design)
- ADR 002 (position-based ranges depend on stack tracking)
- `rangetool/session.py`, `rangetool/config.py`, `rangetool/config.example.yaml`
