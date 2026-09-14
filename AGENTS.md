# AGENTS.md

## Project: poker-repl

A single-module repo containing `rangetool/` — a deterministic Texas Hold'em
preflop decision tool: hand tier-list generator, villain range DSL parser, and
an interactive session REPL for short-stack (3-max, 15bb) push/fold spots.

## Repository conventions

- Python interpreter: use the system `python3` binary.
- Development environment: create a repo-local virtual environment
  (`python3 -m venv .venv` at repo root) and install dependencies through
  `rangetool/requirements.txt`. Run all Python invocations through the venv.
- Branch naming: `#NNNNN` (e.g. `#00001`).
- Commit message format: `#NNNNN + conventional commits`, for example
  `#00001 feat(rangetool): add deterministic hand tier-list generator`.
- Generated `output/` directories are gitignored; never commit CSVs, caches, or
  session artifacts.

---

## Module: rangetool

### Goal
Generate a deterministic, reproducible 169-hand tier-list ranked by heads-up equity
vs. a random hand, with cumulative % from the top. Then allow filtering/highlighting
of that tier-list against a user-supplied "villain range" that does NOT follow GTO
(e.g. "villain shoves any Axo, any pair, and Kxs+") to show which of MY hands are
actually ahead/behind that specific range, not the generic top-X%.

### Requirements

- Language: Python 3.11+.
- Determinism: no `random.sample` without a fixed seed for anything that ends up
  in committed output. Prefer exact enumeration over Monte Carlo wherever the
  combo count is tractable (169 starting hands x remaining deck is fine to enumerate
  exactly for heads-up equity — do NOT use sampling here, use full combinatorial
  enumeration via `itertools.combinations` over all runouts, or an existing
  exact equity library, so output is bit-for-bit reproducible on every run).
- Hand notation: standard 169-hand grid, e.g. `AA`, `AKs`, `AKo`, `72o`.
- Output artifact: `output/hand_tierlist.csv` with columns:
  - `hand` (e.g. `AKs`)
  - `combos` (number of specific card combinations, e.g. 4 for suited, 12 for offsuit, 6 for pairs)
  - `equity_vs_random` (float 0-1, exact heads-up equity vs a uniformly random hand)
  - `cumulative_combos` (running total of combos from strongest hand down)
  - `cumulative_pct` (cumulative_combos / 1326 * 100, rounded to 2 decimals)
- Provide a CLI: `python -m rangetool.tierlist --top-pct 25` prints/exports the
  hands whose cumulative_pct <= 25.
- Provide a CLI: `python -m rangetool.tierlist --top-combos 150` as an alternative
  cutoff by raw combo count instead of percent (percent cutoffs round awkwardly
  at hand boundaries, combo count is more precise).

### Villain range overlay (the actual hard part)

User will describe villain tendencies in loose natural language or shorthand,
e.g.:
  - "villain shoves any Axo, any pair, Kxs+"
  - "villain only shoves premium: 99+, AJs+, AQo+"
  - "villain never folds a pair, shoves any two suited connectors, no offsuit garbage"

Agent must implement a small DSL parser (not a full NLP model) that supports at minimum:
  - Explicit hand lists: `AA, KK, AKs`
  - Range shorthand with `+`: `TT+`, `AJs+`, `KQo+` (meaning that rank pair or better,
    that suited/offsuit combo or better by kicker)
  - Wildcard rank classes: `Axo` (any offsuit ace-x), `Axs` (any suited ace-x),
    `Kxs+` (any suited king-x, x >= some threshold if given, else any x),
    `22+` (any pocket pair)
  - Set operations: union of multiple clauses separated by commas or `;`

Implementation approach:
  - Build a `parse_range(range_string: str) -> set[str]` function that returns the
    exact set of 169 hand-grid labels matching the description. Write unit tests for
    every shorthand pattern above BEFORE wiring it into the CLI.
  - Do NOT use an LLM call at runtime to parse ranges — this must be deterministic
    and instant. Regex + a rank-order lookup table is enough. Reserve LLM assistance
    (if any) for offline dev-time authoring of test cases, not runtime parsing.

Once villain range is parsed into a hand set:
  - Compute `equity_vs_villain_range(my_hand, villain_hand_set)` as an exact
    weighted-average equity of `my_hand` against every hand in the villain set,
    weighted by combo count, excluding blocked combos (card removal: if my_hand
    shares a card with a villain combo, that specific villain combo is impossible
    and must be excluded from the average, not just skipped naively).
  - Output a second CSV: `output/tierlist_vs_villain_range.csv` with columns:
    `hand, equity_vs_random, equity_vs_villain_range, delta, recommendation`
    where `recommendation` is `CALL`/`FOLD` based on a pot-odds threshold the user
    passes as a CLI flag `--pot-odds 0.33` (i.e. call if equity_vs_villain_range >= pot_odds).
  - Sort this second CSV descending by `equity_vs_villain_range` so the user sees
    their best hands vs THIS SPECIFIC villain range at the top, not generic GTO top.

### Testing
  - `tests/test_parse_range.py`: at least 10 cases covering every shorthand above.
  - `tests/test_equity_exact.py`: known reference values, e.g. AA vs KK heads-up
    preflop equity should be ~82%, AKs vs QQ ~46%. Use published exact reference
    numbers as assertions with a tolerance of 0.5%.
  - Full run must be reproducible: running twice with the same inputs produces
    byte-identical CSV output.

---

## General agent behavior rules

- Prefer exact combinatorics over Monte Carlo/sampling anywhere determinism is
  required (rangetool equity calculations). Sampling is only acceptable for
  postflop multi-street simulations if/when this project expands beyond preflop,
  and even then must use a fixed seed and be clearly labeled as an approximation.
- Commit `output/` artifacts to `.gitignore` — these are generated, not source.
- All communication with the user (chat responses, explanations, questions,
  clarifications) must be in Russian. Code, comments, variable names, commit
  messages, and this AGENTS.md file itself remain in English — only the agent's
  conversational output to the user should switch to Russian.
