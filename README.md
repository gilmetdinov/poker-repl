# poker-repl

An interactive Texas Hold'em **preflop decision tool** for short-stack push/fold
spots. Deterministic, reproducible, no runtime LLM — everything is exact
combinatorics.

Built around `rangetool`, a Python package that:

- generates a **169-hand tier-list** ranked by heads-up equity vs a random hand,
  with cumulative combo percentages;
- parses a human-friendly **range DSL** (`22+, Axo, Kxs+, AJs+`) into an exact hand
  set, then re-ranks your hands against *that specific villain range*;
- recommends **CALL / FOLD** using pot-odds math with card-removal (blocked combos)
  handled correctly;
- ships an **interactive session REPL** that tracks position rotation, blind levels,
  effective stack, and knockouts during live play.

## Quick start

```bash
git clone git@github.com:gilmetdinov/poker-repl.git
cd poker-repl
python3 -m venv .venv && source .venv/bin/activate
pip install -r rangetool/requirements.txt
```

Build the exact 169×169 preflop equity cache once (resumable, ~30–60 min):

```bash
python -m rangetool --build-cache
```

## Usage

```bash
# Full tier list
python -m rangetool

# Top 25% by cumulative combos
python -m rangetool --top-pct 25

# Evaluate specific hands vs a villain range
python -m rangetool --hands AKs,AQo,77 --villain-range "22+, Axo, Kxs+" --pot-odds 0.33
```

### Interactive REPL (live play)

```bash
python -m rangetool.repl
```

```text
(BTN|15bb) > hand AKs
(BTN|15bb) > next
(SB|15bb) > hand 77
(BB|12bb) > knockout BTN
(SB|8bb)  > range BB "22+, Axo"
(SB|8bb)  > status
```

The REPL keeps state across hands: rotates your position, subtracts blinds on
entry, tracks blind levels / effective stack, and re-evaluates EV-first for every
action (push / open / raise / limp / call).

### Range DSL

- Explicit hands: `AA, KK, AKs`
- Pair plus: `TT+`, `22+`
- Suited/offsuit plus by kicker: `AJs+`, `K9s+`, `KQo+`
- Wildcard kickers: `Axo`, `Axs`, `Kxs+`
- Union: clauses separated by `,` or `;`
- Aliases: `any pair`, `any Axo`, `any Axs`, `any Kxs`

## Tests

```bash
pytest rangetool/tests/
```

## Structure

```
rangetool/          the package (tierlist, DSL parser, equity engine, REPL)
rangetool/tests/    unit tests (parser, equity reference values, config, session)
docs/adr/           architecture decision records
```

See `rangetool/README.md` for full documentation.
