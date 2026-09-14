# rangetool

Deterministic 169-hand Texas Hold'em tier-list generator with custom villain range overlays.

## Setup

```bash
cd /path/to/repo
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r rangetool/requirements.txt
```

## Building the equity cache

The first run needs an exact 169×169 preflop equity matrix.  Build it once:

```bash
python -m rangetool --build-cache
```

This takes roughly 30–60 minutes on a modern multi-core machine.  Progress is saved every 10 matchups to `rangetool/output/equity_cache.json`, so the process is resumable if interrupted.

## Usage

Full tier list (default):

```bash
python -m rangetool
```

Top 25% by cumulative combos:

```bash
python -m rangetool --top-pct 25
```

Top 150 combos:

```bash
python -m rangetool --top-combos 150
```

Villain range overlay (full 169-hand grid):

```bash
python -m rangetool --villain-range "22+, Axo, Kxs+" --pot-odds 0.33
```

Calculator mode — evaluate specific hands vs a villain range (useful at the table):

```bash
python -m rangetool --hands AKs,AQo,77 --villain-range "Kxo+,Axo+" --pot-odds 0.33
python -m rangetool --hands AKs --villain-range "22+,Axs+" --pot-odds 0.33 --show-random
```

Presets for JAQKpot (bundled villain range + pot odds):

```bash
python -m rangetool --preset jaqkpot-btn --hands AKs
python -m rangetool --preset jaqkpot-sb --hands 77
python -m rangetool --preset jaqkpot-bb --hands KQs
python -m rangetool --list-presets
```

Recommended shell aliases (add to `~/.zshrc` or `~/.bashrc`):

```bash
alias rt-btn='python -m rangetool --preset jaqkpot-btn --hands'
alias rt-sb='python -m rangetool --preset jaqkpot-sb --hands'
alias rt-bb='python -m rangetool --preset jaqkpot-bb --hands'
```

Then just type:

```bash
rt-btn AKs
rt-sb 77,AKo
```

## Interactive session REPL

For live play, use the session REPL. It keeps state across hands, rotates your
position, tracks blind levels / effective stack, and supports knockouts:

```bash
python -m rangetool.repl
```

### Configuration

Generate a default config file once:

```bash
python -m rangetool.config --init-config
```

This writes `rangetool/config.yaml` in the project directory with default
JAQKpot settings. Edit it to set your preferred blind schedule, default villain
ranges, and push/limp/fold thresholds. See `rangetool/config.example.yaml` for
reference.

### REPL commands

```text
(BTN|15bb) > hand AKs
(BTN|15bb) > next
(SB|15bb) > hand 77
(BB|12bb) > knockout BTN
(SB|12bb) > hand KQs
(SB|12bb) > stack 8
(SB|8bb) > range BB "22+, Axo"
(SB|8bb) > status
(SB|8bb) > quit
```

Run non-interactively for scripts/tests:

```bash
python -m rangetool.repl --table-size 3 --stack-bb 15 --elapsed-min 0 --hero-position BTN
```

All CSVs are written to `rangetool/output/`.

## Range DSL

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
