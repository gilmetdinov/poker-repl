# Contributor guide

Short brief for anyone (human or coding agent) changing this repository.
User-facing documentation lives in `README.md`; design decisions in `docs/adr/`.

## Layout

- `rangetool/hands.py`, `cards.py`: the 169-hand grid, combos, canonical combos.
- `rangetool/equity.py`, `cache.py`: exact equity enumeration and the matrix cache
  (`data/equity_cache.json` is bundled; `--build-cache` writes `output/equity_cache.json`).
- `rangetool/range_parser.py`: the range DSL (`parse_range`).
- `rangetool/tierlist.py`, `cli.py`, `presets.py`: tier list, villain overlay, calculator.
- `rangetool/config.py`, `session.py`, `strategy.py`, `repl.py`: the session REPL.
- `rangetool/tests/`: pytest suite.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
mypy rangetool
```

`python -m rangetool --build-cache` uses every CPU core for roughly 50 minutes.
Do not run it casually; the bundled matrix is enough for development and tests.

## Conventions

- Python 3.11+ with type hints; `mypy rangetool` must stay clean.
- Determinism: exact enumeration, no sampling, no runtime network or LLM calls.
- Range strings use standard notation (`ATo+` = ATo..AKo); add a parser test for
  every new DSL form.
- Generated files (`rangetool/output/`, CSVs, a rebuilt cache) are not committed.
- Keep `rangetool/config.example.yaml` identical to the defaults in `config.py`.
- Conventional commit messages (`feat(rangetool): ...`, `fix: ...`).
