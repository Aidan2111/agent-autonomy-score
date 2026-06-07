# Agent Autonomy Score

A lightweight scoring tool for deciding how much supervision AI coding agents need before and after they write code.

The premise is simple: not every code change deserves the same agent workflow. A SwiftUI copy tweak and a Core Data migration should not pass through the same autonomy gate.

This repo turns that idea into a small, inspectable CLI that scores an implementation intent, a code diff, or both from 1 to 10 and recommends one of three modes:

| Score | Band | Recommended mode |
| --- | --- | --- |
| 1-3 | Low Risk | Unsupervised |
| 4-7 | Medium Risk | Guided Autonomy |
| 8-10 | High Risk | Pair Programming |

## Why this exists

AI agents are getting good enough to handle real implementation work, but teams still need a practical threshold for when to trust the pipeline and when to slow it down.

This project uses old-school engineering signals as a first pass:

- Intent risk before work: task wording that points to auth, persistence, migrations, broad refactors, unclear scope, or missing validation.
- Big O risk: nested iteration and algorithm-heavy changes.
- Cyclomatic complexity proxy: broad diffs, directory spread, and branching-sensitive areas.
- Blast radius: state, persistence, auth, pipeline, cache, billing, and migration code.
- State vs presentation: UI-only changes are usually safer than data mutation and storage changes.
- Validation: risky production changes with no tests in the diff get extra scrutiny.

The model is intentionally heuristic. It is a guardrail for agentic SDLC systems, not a replacement for code review.

The key distinction:

- Intent scoring happens before work starts. It predicts how much autonomy an agent should get.
- Diff scoring happens after work is done. It verifies what the agent actually changed.
- Gate scoring uses both. The higher risk wins.

## Quick Start

```bash
python -m pip install -e .
autonomy-score --diff examples/swiftui-copy-change.diff
```

Score a feature request before an agent starts coding:

```bash
autonomy-score --intent examples/intent-core-data-migration.txt
```

Score a pull request diff in an existing repo:

```bash
git diff --unified=3 origin/main...HEAD | autonomy-score --format markdown
```

Score the original intent and the final diff together:

```bash
autonomy-score --intent examples/intent-swiftui-copy.txt --diff examples/core-data-migration.diff
```

Fail a CI step if the diff exceeds your autonomy threshold:

```bash
autonomy-score --diff pr.diff --max-score 7
```

Add an optional LLM second opinion:

```bash
python -m pip install -e ".[llm]"
export OPENAI_API_KEY="sk-your-key"
autonomy-score --diff examples/core-data-migration.diff --llm-analysis
```

On Windows PowerShell:

```powershell
python -m pip install -e ".[llm]"
$env:OPENAI_API_KEY = "sk-your-key"
python -m autonomy_score --diff examples\core-data-migration.diff --llm-analysis
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

## Before And After Work

Use intent scoring at issue triage time:

```bash
autonomy-score --intent issue.txt --max-score 3
```

That answers: "Can an agent start this unsupervised?"

Use diff scoring once code exists:

```bash
autonomy-score --diff pr.diff --max-score 7
```

That answers: "How much human review does this PR need?"

Use both when you have the original request and the final implementation:

```bash
autonomy-score --intent issue.txt --diff pr.diff --format markdown
```

That answers: "Did the implementation stay inside the autonomy envelope?" If the intent looked low-risk but the diff touches persistence, auth, migrations, or broad architecture, the gate score rises to the diff score.

## Repo Tour

- `src/autonomy_score/`: CLI, diff parser, and scoring model.
- `examples/`: sample intents and diffs that demonstrate low, medium, and high risk.
- `docs/scoring-model.md`: scoring rules and calibration notes.
- `docs/case-study.md`: product and engineering framing behind the project.
- `.github/workflows/autonomy-score.yml`: example GitHub Actions integration.

## Configuration

You can override the default scoring terms with a JSON config:

```bash
autonomy-score --diff pr.diff --config autonomy-score.config.json
```

See `autonomy-score.config.json` for the default shape. Teams can tune path terms and content terms to match their architecture.

## Optional LLM Advisory Analysis

The deterministic score is always the source of truth. If you pass `--llm-analysis`, the CLI asks an OpenAI-compatible model for a structured second opinion and adds an `llm_analysis` section to the output.

The LLM cannot change `score`, `band`, or `recommended_mode`. It can only report:

- agreement with the deterministic result
- risk summary
- missed risks
- possible false positives
- recommended human action
- confidence

Configuration:

```bash
autonomy-score --diff pr.diff --llm-analysis --llm-model gpt-4.1-mini
```

Environment variables:

- `OPENAI_API_KEY`: required when `--llm-analysis` is used
- `OPENAI_BASE_URL`: optional OpenAI-compatible endpoint
- `AUTONOMY_SCORE_LLM_MODEL`: optional model default

This project intentionally does not use Google ADK as a core dependency yet. ADK is compelling when you need workflow agents, tools, runners, sessions, and local runtime inspection, but this v1 CLI only needs a deterministic scorer plus an optional advisory review pass. See [Google ADK overview](https://adk.dev/get-started/about/) and [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

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
- Add a separate Google ADK demo once the project needs real multi-agent orchestration.
- Support policy presets for startup, enterprise, regulated, and high-trust teams.

## License

MIT
