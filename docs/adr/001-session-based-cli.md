# ADR 001: Session-based CLI

## Status

Accepted

## Context

`rangetool` started as a one-shot command-line utility: it computes exact
heads-up preflop equity for the 169-hand grid, overlays a user-defined villain
range and checks specific hands against a pot-odds threshold.

The main study use case is short-stack push/fold play in small tournaments:

- 3-max tables that end heads-up.
- 15 bb starting stacks.
- Blind levels that rise every few minutes, so effective stacks shrink quickly.
- Preflop all-in decisions dominate; post-flop play is rare.

Reviewing a sequence of hands from such a tournament with the one-shot CLI
means re-typing the position, the stack, the villain range and the pot odds for
every hand. Most of that information follows mechanically from the previous
hand: the button moves, blinds are posted, levels change, players bust.

## Decision

Add an interactive session REPL (`python -m rangetool.repl`, built on
`cmd.Cmd`) that keeps the tournament state between hands. The user drives it by
typing commands. It reads nothing except its own config file and the equity
matrix, and makes no network calls.

### Configuration and state

- **Config** (`rangetool/config.yaml`, built-in defaults when absent,
  documented in `rangetool/config.example.yaml`):
  - `table_size` (3 or 2) and `starting_stack_bb` (15)
  - blind schedule: big-blind chip value and duration per level
  - default villain range per seat (BTN, SB, BB)
  - hero push/call ranges per seat (ADR 002, ADR 004)
  - decision thresholds (`ev_margin`, `fold_equity`)
- **Session state** (set at start-up or changed by commands):
  - hero seat
  - active seats (updated on knockouts)
  - effective stack in bb
  - elapsed time and current blind level
  - per-seat villain range overrides

### Commands

| Command | Effect |
|---|---|
| `hand <hand> [open\|push\|raise\|limp]`, `h`, or a bare hand label | evaluate a hand in the current spot |
| `next`, `n` | rotate the hero seat and deduct the blind for the new seat (ADR 003) |
| `pos <seat>` | set the hero seat |
| `stack <bb>` | override the effective stack |
| `level <n>`, `time <min>` | move to a blind level; the stack in bb is rescaled (ADR 003) |
| `range <seat> "<range>"`, `ranges` | override or list villain ranges |
| `knockout <seat>`, `ko` | remove a seat; with two seats left the table is heads-up |
| `status`, `help`, `quit` | |

The hero seat rotates BTN → BB → SB → BTN (the button moves clockwise) and
SB ↔ BB heads-up. After a knockout a 3-max seat maps to its heads-up
equivalent (BTN → SB).

### Recommendations

Each `hand` command prints the equity against the villain range, the EV of
the decision in bb, the hero range in effect at the current stack and a
PUSH/FOLD verdict with its reason. The decision logic is described in ADR 002.
When the opponent has shoved (`push`), the required equity is derived from the
session state (effective stack and blinds), so no pot-odds flag is needed.

## Consequences

### Positive

- No repeated input: position, stack and blind level follow from the
  previous hand.
- Fewer input mistakes, because blinds and level changes are applied
  mechanically.
- Position-aware ranges and automatic pot odds give more specific answers
  than a generic equity calculator.
- Fully offline and deterministic.

### Negative / risks

- More code than the one-shot CLI: config, session state and strategy layers.
- The state is only as accurate as what the user types. A missed `next` or
  `knockout` puts the session out of step.
- Session state is in memory only and is lost on exit.

## Alternatives considered

1. **Keep the one-shot CLI only.** Rejected: too much repeated input per hand.
2. **Web app UI.** Rejected for now: adds frontend complexity. A local REPL
   is faster to iterate on and needs no network.
3. **Pre-built push/fold charts from day one.** Rejected: equity-driven
   recommendations come first. Charts can be checked against them later.

## Related

- ADR 002 (position ranges, action-aware decisions, EV output)
- ADR 003 (blind deduction and blind schedule)
- ADR 004 (range interpolation)
- `rangetool/repl.py`, `rangetool/session.py`, `rangetool/config.py`
