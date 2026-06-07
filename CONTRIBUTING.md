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

The scoring model should stay deterministic. If you add a new signal, include at least one test that explains the intended behavior.

## Calibration Notes

Please describe the team context behind any scoring change. For example, a payment system, an internal dashboard, and a prototype mobile app may have different autonomy thresholds.

