# Operations

This is not an Azure-hosted workload. The Microsoft Well-Architected Framework is used here as a practical review lens for the repository, CLI, and GitHub workflow.

## Reliability

- Keep deterministic scoring as the source of truth.
- Run unit tests for parser, scorer, CLI, optional LLM validation, and documentation references.
- Keep `--max-score` as the CI-friendly gate for teams that want to fail risky changes.
- Treat inputs above the CLI limits as manual review events:
  - intent input: 100 KB
  - diff input: 2 MB

Local verification:

```bash
uv run --python 3.12 --with-editable . python -m unittest discover -s tests
uv build
```

## Security

- Never commit real API keys. Use `.env.example` only as a template.
- Keep `OPENAI_API_KEY` in the caller environment when `--llm-analysis` is used.
- Keep deterministic scoring authoritative; model output is advisory only.
- In CI, load `autonomy-score.config.json` from a protected branch, release artifact, or organization-controlled location.
- Keep GitHub Actions permissions minimal. The default workflow only needs `contents: read`.
- Use private vulnerability reporting for suspected security issues.

## Cost Optimization

- Keep the core CLI dependency-free and local by default.
- Do not enable LLM analysis in default CI. It requires network calls and can create avoidable spend.
- Bound diff text sent to the optional LLM layer. The provider sees at most 60,000 diff characters.
- Avoid adding heavyweight framework dependencies until a concrete workflow needs them.

## Operational Excellence

- Use GitHub Flow: create a focused branch, open a PR, run checks, review, merge, and delete the branch.
- Keep `main` releasable. Do not use it for speculative work.
- Require tests for scoring changes and docs reference tests for moved examples.
- Use the pull request template to record validation and security impact.
- Keep release notes tied to observable CLI behavior: scoring signals, output format, config compatibility, and CI behavior.

## Performance Efficiency

- Parse unified diffs instead of indexing entire repositories.
- Avoid AST or language-server work in the core path until a benchmarked need exists.
- Keep input-size limits explicit so the tool fails fast on oversized changes.
- Add per-language analyzers behind optional modules or config once they prove value.

## Incident Checklist

Use this checklist when a scoring bug, misleading output, or CI failure affects users:

1. Reproduce with a small intent or diff fixture.
2. Add a failing unit test that captures the bad scoring or output.
3. Fix the deterministic code path.
4. Run the full local verification commands.
5. Document the behavior change in `docs/scoring/model.md` or release notes.
6. If a vulnerable dependency or secret exposure is involved, follow `SECURITY.md`.

## References

- https://learn.microsoft.com/en-us/azure/well-architected/pillars
- https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/principles
