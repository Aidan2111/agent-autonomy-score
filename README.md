# Agent Autonomy Score

A lightweight scoring tool for deciding how much supervision AI coding agents need before they are allowed to write code and open a pull request.

The premise is simple: not every code change deserves the same agent workflow. A SwiftUI copy tweak and a Core Data migration should not pass through the same autonomy gate.

This repo turns that idea into a small, inspectable CLI that scores a diff from 1 to 10 and recommends one of three modes:

| Score | Band | Recommended mode |
| --- | --- | --- |
| 1-3 | Low Risk | Unsupervised |
| 4-7 | Medium Risk | Guided Autonomy |
| 8-10 | High Risk | Pair Programming |

## Why this exists

AI agents are getting good enough to handle real implementation work, but teams still need a practical threshold for when to trust the pipeline and when to slow it down.

This project uses old-school engineering signals as a first pass:

- Big O risk: nested iteration and algorithm-heavy changes.
- Cyclomatic complexity proxy: broad diffs, directory spread, and branching-sensitive areas.
- Blast radius: state, persistence, auth, pipeline, cache, billing, and migration code.
- State vs presentation: UI-only changes are usually safer than data mutation and storage changes.
- Validation: risky production changes with no tests in the diff get extra scrutiny.

The model is intentionally heuristic. It is a guardrail for agentic SDLC systems, not a replacement for code review.

## Quick Start

```bash
python -m pip install -e .
autonomy-score --diff examples/swiftui-copy-change.diff
```

Score a pull request diff in an existing repo:

```bash
git diff --unified=3 origin/main...HEAD | autonomy-score --format markdown
```

Fail a CI step if the diff exceeds your autonomy threshold:

```bash
autonomy-score --diff pr.diff --max-score 7
```

## Example Output

```text
Autonomy Score: 1/10 (Low Risk)
Recommended mode: Unsupervised
Summary: Agent can implement feedback, write code, and open a PR with normal review.
Files changed: 1
Lines added/removed: +8/-1

Signals:
- cap presentation-only-cap: All changed files look like presentation, copy, style, or preview work. [App/Views/ProfileView.swift]
```

## Recommended Workflows

Low Risk, 1-3:

Let the agent process feedback, make the change, run local checks, and open a PR. Human review still happens at the PR boundary.

Medium Risk, 4-7:

Ask the agent to propose an approach first. A human approves the architecture, then the agent can implement the approved plan.

High Risk, 8-10:

Keep the human actively in the loop. The agent can inspect, draft, test, and explain, but should not drive the implementation alone.

## Repo Tour

- `src/autonomy_score/`: CLI, diff parser, and scoring model.
- `examples/`: sample diffs that demonstrate low, medium, and high risk.
- `docs/scoring-model.md`: scoring rules and calibration notes.
- `docs/case-study.md`: product and engineering framing behind the project.
- `.github/workflows/autonomy-score.yml`: example GitHub Actions integration.

## Configuration

You can override the default scoring terms with a JSON config:

```bash
autonomy-score --diff pr.diff --config autonomy-score.config.json
```

See `autonomy-score.config.json` for the default shape. Teams can tune path terms and content terms to match their architecture.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```

Run the CLI without installing:

```bash
PYTHONPATH=src python -m autonomy_score --diff examples/core-data-migration.diff
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m autonomy_score --diff examples/core-data-migration.diff
```

## Roadmap

- Add SARIF output for code scanning surfaces.
- Add per-language analyzers for Swift, TypeScript, and Python.
- Add GitHub PR comments with the autonomy recommendation.
- Calibrate scores against real agent success and rollback data.
- Support policy presets for startup, enterprise, regulated, and high-trust teams.

## License

MIT
