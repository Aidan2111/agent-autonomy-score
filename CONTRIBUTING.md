# Contributing

Thanks for considering a contribution.

This project is intentionally small and explainable. Contributions should make the autonomy score more useful without hiding the reasoning behind a black box.

## Good First Contributions

- Add realistic sample diffs from another language or framework.
- Tune path and content signals for a specific architecture.
- Improve Markdown, JSON, or CI output.
- Add tests for a false positive or false negative.

## Development

```bash
python -m unittest discover -s tests
```

For parity with CI:

```bash
uv run --python 3.12 --with-editable . python -m unittest discover -s tests
```

The scoring model should stay deterministic. If you add a new signal, include at least one test that explains the intended behavior.

## Branch and Pull Request Flow

Use GitHub Flow for normal work:

1. Create a focused branch from `main`, such as `feat/new-signal`, `fix/parser-case`, `docs/scoring-note`, or `chore/ci-cleanup`.
2. Keep unrelated changes out of the branch.
3. Open a pull request with validation evidence.
4. Merge only after checks pass.
5. Delete the branch after merge.

See `docs/operations/branching-and-releases.md` for recommended `main` protection and release steps.

## Repository Structure

- Put package code in `src/autonomy_score/`.
- Put parser, scorer, CLI, and LLM changes behind their existing module boundaries.
- Put diff fixtures in `examples/diffs/`.
- Put intent fixtures in `examples/intents/`.
- Put known complexity-boundary fixtures in `examples/complexity/`.
- Update `docs/scoring/model.md` when a scoring rule, threshold, or known limitation changes.
- Update `docs/engineering/architecture.md` when package boundaries or data flow change.

## Calibration Notes

Please describe the team context behind any scoring change. For example, a payment system, an internal dashboard, and a prototype mobile app may have different autonomy thresholds.
