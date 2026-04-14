# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the application code, grouped by domain: `ai/`, `analysis/`, `cli/`, `core/`, `data/`, and `report/`. The CLI entrypoint lives in `src/cli/main.py`. Keep tests under `tests/` and mirror the source layout where possible, for example `src/core/scorer.py` with `tests/core/test_scorer.py`. Utility scripts belong in `scripts/`. Use `data/samples/` for safe example inputs, and treat `reports/` as generated output rather than source.

## Build, Test, and Development Commands
Install development dependencies first:

```bash
pip install -e ".[dev]"
```

Common commands:

```bash
pytest
pytest tests/core/test_scorer.py -x
ruff check src/ tests/
ruff format src/ tests/
python -m src.cli.main --help
```

`pytest` runs the full suite. The single-file example is useful for fast debugging. `ruff check` enforces lint rules, and `ruff format` applies the repository style. `python -m src.cli.main --help` is the quickest way to inspect CLI behavior during development before installing the package script.

## Coding Style & Naming Conventions
Use Python 3.10+, 4-space indentation, and the Ruff line length of 100. Prefer absolute imports across packages. Use `snake_case` for modules, files, and functions, and `PascalCase` for classes. Add new code to the closest existing domain package instead of creating generic helpers at the repository root.

## Testing Guidelines
Use `pytest` for all tests and name files `test_*.py`. New work should cover edge cases in scoring rules, parsers, data loading, CLI branches, and AI adapters. Run focused tests while iterating, then run `pytest` before merging changes that affect matching, recommendation, or report generation.

## Commit & Pull Request Guidelines
Recent history uses short prefixes such as `feat:` and `refactor:`. Keep commit messages concise and imperative, for example `fix: handle empty salary range`. Pull requests should state the goal, affected modules, and test commands run. Include sample output or screenshots when CLI behavior or generated HTML reports change.

## Security & Configuration Tips
AI features require the `ZHIPU_API_KEY` environment variable. Do not commit real resumes, scraped job data, or generated reports. Prefer sample fixtures from `data/samples/` when writing tests, examples, or bug reproductions.

## Contributor Workflow Notes
Reuse the current package boundaries whenever possible: scoring belongs in `src/core/`, market summaries in `src/analysis/`, and HTML rendering in `src/report/`. When behavior changes, update the matching tests and refresh any relevant command examples in `README.md`. Scripts in `scripts/` should remain runnable and should not accumulate one-off debugging code.
