# poker-repl

`rangetool` is an offline study and review tool for preflop push/fold decisions
in short-stack Texas Hold'em tournaments (3-max or heads-up, 15 bb and below).
You describe a spot by typing it in; the tool answers with exact equities, the
EV of shoving or calling, and a PUSH/CALL/FOLD verdict with the reason.

It has two front ends over the same engine:

- a **command-line calculator**: a 169-hand tier list ranked by equity against a
  random hand, a re-ranking of all hands against a villain range you specify,
  and a pot-odds check for specific hands;
- a **session REPL** for reviewing a sequence of hands: it tracks position
  rotation, posted blinds, blind levels, the effective stack and knocked-out
  players, so you only type the hand and what the opponent did.

Everything is deterministic: equities come from full enumeration of every
board, there is no sampling and no network access.

## Install

Python 3.11+.

```bash
git clone https://github.com/gilmetdinov/poker-repl.git
cd poker-repl
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # or: pip install .   (runtime only)
```

The package ships a prebuilt 169×169 equity matrix (`rangetool/data/equity_cache.json`),
so it works immediately after installation.

## Quick start

Top 5% of starting hands by equity against a random hand:

```text
$ python -m rangetool --top-pct 5
hand  combos  equity_vs_random  cumulative_combos  cumulative_pct
-----------------------------------------------------------------
AA    6       0.8539            6                  0.45
KK    6       0.8253            12                 0.90
QQ    6       0.8000            18                 1.36
JJ    6       0.7750            24                 1.81
TT    6       0.7501            30                 2.26
99    6       0.7203            36                 2.71
88    6       0.6911            42                 3.17
AKs   4       0.6740            46                 3.47
AQs   4       0.6656            50                 3.77
77    6       0.6617            56                 4.22

Wrote rangetool/output/hand_tierlist.csv
```

Should these hands call a shove from a fairly tight range, given that a call
needs 47% equity?

```text
$ python -m rangetool --hands AKs,A5s,KTo,77,J9s --villain-range "22+, A2s+, ATo+, KQs" --pot-odds 0.47 --show-random
hand  combos  equity_vs_villain_range  recommendation  equity_vs_random  delta
------------------------------------------------------------------------------
AKs   4       0.5776                   CALL            0.6740            -0.0964
A5s   4       0.3748                   FOLD            0.6015            -0.2267
KTo   12      0.3668                   FOLD            0.6018            -0.2350
77    6       0.5173                   CALL            0.6617            -0.1445
J9s   4       0.3840                   FOLD            0.5544            -0.1704
```

Review a few hands of a 3-max session that starts at 15 bb on the button
(first three commands):

```text
$ python -m rangetool.repl --table-size 3 --stack-bb 15 --elapsed-min 0 --hero-position BTN
Starting new rangetool session...

Rangetool session REPL. Type 'help' for commands, 'quit' to exit.

(BTN|15.0bb) > hand AKs
AKs (4 combos)
  Hero position: BTN
  Action: open (hero is first in and decides whether to shove)
  Villain range: 49 hands
  Equity vs villain range: 65.37%
  Effective stack: 15.0bb
  EV of shoving: +3.96 bb  |  Assumed fold equity: 40%
  Range for this spot: 62 hands
  Recommendation: PUSH
  Reason: AKs: +EV (+3.96bb) and in the 62-hand push range
(BTN|15.0bb) > next
Next hand: hero BB
(BB|14.0bb) > QJo
QJo (12 combos)
  Hero position: BB
  Action: open (hero is first in and decides whether to shove)
  Villain range: 59 hands
  Equity vs villain range: 42.60%
  Effective stack: 14.0bb
  EV of shoving: -0.26 bb  |  Assumed fold equity: 40%
  Range for this spot: 88 hands
  Recommendation: FOLD
  Reason: QJo: -EV (-0.26bb) even though it is in the 88-hand push range
```

## CLI reference

```bash
python -m rangetool                          # full 169-hand tier list (also written to CSV)
python -m rangetool --top-pct 25             # cut by cumulative percent of all 1326 combos
python -m rangetool --top-combos 150         # cut by cumulative combo count
python -m rangetool --villain-range "22+, Axo, Kxs+" --pot-odds 0.33   # tier list + overlay vs a range
python -m rangetool --hands AKs,AQo,77 --villain-range "22+, Axo" --pot-odds 0.33
python -m rangetool --list-presets           # bundled villain range + pot-odds presets
python -m rangetool --preset 3max-hyper-sb --hands KQs,A5o
```

CSV files go to `rangetool/output/` (`--output-dir` to change). After
`pip install`, the same commands are available as `rangetool ...`.

## Session REPL

```bash
python -m rangetool.repl [--table-size 2|3] [--stack-bb N] [--elapsed-min M] [--hero-position BTN|SB|BB] [--config PATH]
```

Values you leave out are asked for at start-up.

| Command | Meaning |
|---|---|
| `hand <hand> [open\|push\|raise\|limp]`, `h`, or just `<hand>` | evaluate a hand; `push` means the opponent shoved and you decide whether to call |
| `next`, `n` | next hand: rotate position (BTN → BB → SB) and deduct the blind for the new seat |
| `pos <seat>` | set your seat |
| `stack <bb>` | set the effective stack (decimals allowed) |
| `level <n>` / `time <min>` | jump to a blind level; the stack in bb is rescaled by the big-blind ratio |
| `range <seat> "<range>"` / `ranges` | override / list villain ranges by seat |
| `knockout <seat>`, `ko` | remove a player; with two left the table becomes heads-up |
| `status`, `help`, `quit` | |

Configuration (blind schedule, villain ranges per seat, hero push/call ranges,
thresholds) has built-in defaults. To customise it:

```bash
python -m rangetool.config --init-config    # writes rangetool/config.yaml
```

`rangetool/config.example.yaml` documents every field and equals the defaults.

## Range DSL

Comma- or semicolon-separated tokens, case-insensitive:

| Token | Expands to |
|---|---|
| `AA, AKs, 72o` | exactly those hands |
| `77+` | 77, 88, 99, TT, JJ, QQ, KK, AA |
| `ATo+` | ATo, AJo, AQo, AKo (kicker rises, high card fixed) |
| `KJs+` | KJs, KQs |
| `KQo+` | KQo |
| `Axs` / `Axo` | all 12 suited / offsuit aces |
| `Kxs+` | every suited hand with a king or ace as high card (23 hands) |
| `any pair`, `any Axs`, `any Axo`, `any Kxs` | aliases for `22+`, `Axs`, `Axo`, `Kxs` |

## How a decision is computed

1. **Equity matrix.** Each of the 169 hand classes is represented by one fixed
   suit combination. For every pair of classes the tool enumerates all
   C(48,5) = 1,712,304 boards with the `phevaluator` hand evaluator. That is
   14,196 class matchups plus the diagonal; the result is the bundled matrix.
2. **Equity against a range** is the average over the villain's classes,
   weighted by how many of each class's combos remain once the cards in your
   hand are removed (card removal). Equity against a random hand is the same
   average over all 169 classes.
3. **Calculator:** `CALL` if equity against the villain range ≥ `--pot-odds`.
4. **REPL:** the villain is the next seat clockwise, with that seat's default
   or overridden range. With effective stack S and blinds of 1.5 bb in the pot:
   - first in, or over a raise or limp (`open`/`raise`/`limp`):
     EV = f·1.5 + (1 − f)·(eq·(1.5 + 2S) − S), where f is the fold-equity setting (default 40%);
   - facing a shove (`push`): EV = eq·(1.5 + 2S) − S; required equity S / (1.5 + 2S).

   EV ≥ +0.02 bb gives PUSH, EV below −0.02 bb gives FOLD. In between, the
   configured hero range for your seat decides. That range moves from a
   "deep" to a "wide" version as the stack shrinks (see ADR 004). At or below
   0.5 bb the verdict is to push any two cards.

## Limitations

- **Approximate matrix.** One representative suit combination per class means
  suit interactions between the two hands (for example AKs vs QQ with or
  without a shared suit) are not averaged. The reference tests (AA vs KK,
  AKs vs QQ, AA and 72o vs random) agree with published equities within half a
  percentage point.
- **Fixed fold equity.** Every open shove assumes the same probability that
  the opponent folds (`thresholds.fold_equity`, default 40%), regardless of
  seat, stack or range.
- **Open-shove equity uses the opponent's whole range**, not just the part of
  it that would call. Calling ranges are stronger, so this usually overstates
  how well you do when called.
- **Simplified pot.** The pot is always the 1.5 bb of blinds. Antes, the extra
  chips in a raise or limp, and a blind you have already posted are not
  counted. Raise and limp spots are evaluated as open shoves.
- **One opponent.** The villain is always the next seat clockwise, even when
  that seat could not have acted (for example `push` on the button), and a
  3-max shove is modelled heads-up against that single player.
- **Chip EV only.** There is no ICM or payout model.
- **Default ranges are hand-written study defaults**, not solver output.
  Session state lives in memory and is lost when you quit.

## Rebuilding the equity matrix (optional)

```bash
python -m rangetool --build-cache
```

This recomputes the full matrix into `rangetool/output/equity_cache.json`
using all CPU cores. It takes roughly 50 minutes on a recent multi-core
laptop, saves progress every 100 matchups and resumes if interrupted. Once
that file exists it takes precedence over the bundled matrix; delete it to go
back to the bundled one.

## Tests and type checking

```bash
pytest            # or: python -m pytest
mypy rangetool
```

103 tests. Two of them enumerate one matchup each from scratch (AA vs KK,
AKs vs QQ), which takes a few seconds. Everything else reads the bundled matrix.

## Layout

```
rangetool/            package: equity engine, range DSL, tier list, CLI, session REPL
rangetool/data/       bundled equity matrix
rangetool/tests/      unit tests
docs/adr/             four architecture decision records
```
