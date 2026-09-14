# ADR 001: Session-based CLI and long-term automation vision for rangetool

## Status

Proposed

## Context

`rangetool` started as a one-shot command-line utility that computes exact
heads-up preflop equity for a 169-hand grid and overlays user-defined villain
ranges.  The immediate use case, however, is in-game assistance at Stake
JAQKpot sit-and-go tournaments:

- 3-max tables.
- 15 bb starting stacks.
- Blind levels increase over time, so effective stacks shrink.
- Pre-flop decisions dominate the game; large opens and post-flop maneuvering
  are rare.
- The user needs sub-second feedback while playing, not a batch CSV export.

A single CLI invocation per hand is too slow for this environment: the user
must repeatedly re-type ranges, positions, stack sizes, and pot odds.  We
therefore need a stateful session interface and, eventually, automated screen
reading.

## Decision

We will evolve `rangetool` through clearly separated phases:

1. **Core engine (done/in progress)** — exact 169×169 equity matrix, DSL range
   parser, one-shot CLI, persistent JSON cache.
2. **Session REPL** — an interactive command loop that keeps game state across
   hands.
3. **JAQKpot strategy layer** — push/limp/fold recommendations tuned to
   3-max/15 bb play, with automatic range widening as effective stacks shrink.
4. **Screen capture + OCR/vision** — read the Stake client from screenshots
   only (no injection, no DOM manipulation).
5. **Read-only decision assistant** — display notifications and a decision
   guide; never perform clicks or direct inputs on the client.

### Session REPL design

The REPL maintains two levels of configuration:

- **Global config (`~/.config/rangetool/config.yaml` or project config)**
  - `table_size` (default 3 for JAQKpot)
  - `starting_stack_bb` (default 15)
  - **Blind level schedule** — level duration and small/big blind amounts so
    the tool can track the current effective stack over time.
  - Default villain ranges **per position** (BTN, SB, BB)
  - Equity thresholds mapping to actions
- **Per-session state** (set at REPL start or mutated via commands)
  - `hero_position` — set by the user each session because seating is random
  - Active opponents and their positions (updated when a player is knocked
    out)
  - Current effective stack in bb
  - Session-specific overrides of villain ranges
  - Current rotation index (auto-advanced after each hand)

Example REPL flow:

```text
$ python -m rangetool.session
Table size [3]:
Blind schedule [5/10@0,10/20@5,15/30@10]:
Starting stack bb [15]:
Hero position (BTN/SB/BB): SB

(SB) > hand AKs
AKs vs BTN range: 68.3% equity at 14.2bb effective → PUSH
Pot needs: 45.2%  |  auto pot odds: shove 14bb into 16.5bb

(BB) > hand 77
77 vs SB range at 13.5bb: 51.1% equity → LIMP/FOLD

(BTN) > knockout BB
Heads-up mode. Hero position: SB

(SB) > hand K8s
K8s vs BB range at 9.1bb: 47.8% equity → PUSH
```

The REPL auto-rotates `hero_position` after each hand in the natural order:
BTN → SB → BB → BTN.  When an opponent is knocked out, the user runs a
`knockout <seat>` command and the session switches to heads-up mode.

### Effective stack and blind levels

Effective stack is tracked in bb and decreases automatically as blind levels
advance.  The tool can also accept manual stack updates:

- `stack <bb>` — override current effective stack.
- `level <n>` / `time <min>` — jump to a specific blind level or elapsed time.

As stacks get shorter, push/fold ranges widen.  The strategy layer uses the
current effective stack to select appropriate default villain ranges and
recommendation thresholds.

### Action mapping

Because JAQKpot starts at 15 bb, classic raise/fold sizing is replaced by a
push/limp/fold model:

| Equity vs villain range | Recommendation |
|--------------------------|----------------|
| ≥ upper threshold (~55–60% at 15bb, lower as stacks shrink) | PUSH (all-in) |
| middle band (~42–55%)    | LIMP / marginal |
| < lower threshold (~42%) | FOLD |

Thresholds are configurable per effective stack depth and may later be
replaced by pre-computed Nash push/fold charts for 3-max and heads-up play.

### Auto pot odds

Pot odds are derived automatically from the session state:

- Known current pot size (default or read from screen later).
- Known villain action (limp/shove) and stack sizes.
- No manual `pot-odds` flag is required during play.

### Vision automation

All automation reads pixels only; it never injects into the Stake client or
intercepts network traffic.  This minimizes ban risk.

Possible implementation stack for screen reading on macOS:

- `screencapture` / `Quartz` / `mss` for screenshots.
- `Apple Vision` framework or lightweight local models for OCR.
- `YOLOv8`/`Ultralytics` for region detection (cards, stacks, buttons).
- Local vision-language models (e.g. Qwen2-VL, Llama 3.2 Vision) on Apple
  Silicon for end-to-end state parsing.

Output is limited to **notifications and a decision guide** shown in a
separate, non-overlapping window or via macOS notifications.  The user acts
manually on the Stake client.

Autonomous clicking and direct mouse/keyboard automation are explicitly out of
scope for the first iterations.  They will only be reconsidered after the
separate `scraper` module has proven reliable at reading history and stats,
and only with strong human-safety gates.

## Consequences

### Positive

- The tool becomes usable in real time at the table.
- Session state removes repetitive input and reduces user error.
- Position-aware ranges, effective-stack tracking, and auto pot odds produce
  more accurate recommendations than a generic equity calculator.
- Pixel-only, read-only automation keeps the project on the safe side of
  platform terms.

### Negative / risks

- Adds significant scope beyond the original one-shot CLI.
- Screen reading requires calibration per client resolution/theme and may be
  brittle after UI updates.
- Local vision models consume battery and GPU; performance must be validated on
  the target MacBook Pro M4 Pro.
- Even read-only screen reading sits in a grey area; we must monitor Stake's
  terms of service.

## Alternatives considered

1. **Keep one-shot CLI only.**  Rejected: too slow for in-game use.
2. **Browser extension / DOM scraping.**  Rejected: high ban risk on Stake and
   conflicts with the scraper module's anti-bot design.
3. **Web app UI.**  Rejected for now: adds frontend complexity; a local REPL
   is faster to iterate and requires no network.
4. **Use pre-built push/fold charts from day one.**  Rejected: we want exact
   equity-driven recommendations first, then calibrate charts against them.
5. **Autonomous clicking with confirmation.**  Rejected for the initial scope:
   too high a ban risk on Stake; defer until after read-only scraper and
   assistant are proven.

## Related

- `rangetool/README.md`
- Future ADR: screen-reading pipeline and vision model selection.
- Future ADR: JAQKpot push/fold/limp strategy engine.
