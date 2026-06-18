# Repository Architecture

Agent Autonomy Score is a small Python CLI. The repository is organized to keep the scoring policy auditable, testable, and easy to run in CI.

## Layout

```text
.
|-- src/autonomy_score/        # Importable package and CLI entry point
|-- tests/                     # Unit and documentation integrity tests
|-- examples/
|   |-- diffs/                 # Realistic pull request diff fixtures
|   |-- intents/               # Pre-work task brief fixtures
|   `-- complexity/            # Known complexity-boundary fixtures
|-- docs/
|   |-- engineering/           # Architecture and durable decisions
|   |-- scoring/               # Scoring rules and optional LLM contract
|   |-- operations/            # Runbook, branching, and release process
|   `-- product/               # Product framing and case study
|-- .github/                   # CI, issue templates, Dependabot, PR template
|-- autonomy-score.config.json # Default policy shape for team customization
`-- pyproject.toml             # Packaging metadata and console script
```

The project intentionally uses a `src/` package layout. Keeping importable code under `src/autonomy_score/` helps tests exercise the installed package instead of accidentally importing loose files from the repository root.

## Runtime Boundaries

- `cli.py` owns argument parsing, bounded input reading, output formatting, git-diff integration, and exit codes.
- `diff_parser.py` owns language-agnostic unified diff parsing.
- `scoring.py` owns deterministic intent, diff, and gate scoring.
- `llm.py` owns optional advisory analysis. It cannot change the deterministic score, band, or recommended mode.
- `__main__.py` and the `autonomy-score` console script delegate to the same CLI path.

The deterministic scorer is the policy authority. The optional LLM layer is intentionally isolated so users can run the core tool without network access, API keys, or model dependencies.

## Data Flow

1. A user supplies intent text, a unified diff, staged changes, a base ref, or stdin.
2. `cli.py` bounds file and stdin sizes before parsing.
3. `diff_parser.py` converts unified diffs into changed-file records.
4. `scoring.py` applies transparent path, content, blast-radius, validation, and complexity-risk signals.
5. `cli.py` renders text, JSON, or Markdown output and enforces `--max-score` if supplied.
6. If `--llm-analysis` is enabled, `llm.py` receives the deterministic result plus a truncated diff and returns advisory fields only.

## Design Constraints

- Keep the core package dependency-free.
- Keep scoring deterministic and explainable.
- Require tests for any new signal or scoring threshold change.
- Keep policy configuration loaded from a trusted source in CI.
- Treat large diffs as manual review events instead of asking the scorer to bless them.

## Design Influences

- Microsoft Azure Well-Architected Framework pillars: reliability, security, cost optimization, operational excellence, and performance efficiency as review lenses for the tool and repo process.
- GitHub Flow: short-lived branches, pull requests, required checks, and protected `main`.
- Python Packaging User Guide: `src/` layout for clearer package/import boundaries.

References:

- https://learn.microsoft.com/en-us/azure/well-architected/pillars
- https://docs.github.com/en/get-started/using-github/github-flow
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
