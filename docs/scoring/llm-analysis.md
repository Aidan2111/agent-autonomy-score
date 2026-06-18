# Optional LLM Advisory Analysis

The core scorer is deterministic by design. It should be easy to inspect, test, and tune without trusting a model call.

`--llm-analysis` adds a second opinion on top of that deterministic result. The model reviews the same diff and score signals, then returns structured JSON with advisory fields only.

## Contract

The LLM cannot change:

- `score`
- `band`
- `recommended_mode`

The LLM can add:

- `agreement`: `agree`, `partially_agree`, or `disagree`
- `risk_summary`
- `missed_risks`
- `possible_false_positives`
- `recommended_human_action`
- `confidence`: `low`, `medium`, or `high`

## Local Usage

```bash
python -m pip install -e ".[llm]"
export OPENAI_API_KEY="sk-your-key"
autonomy-score --diff examples/diffs/core-data-migration.diff --llm-analysis
```

Windows PowerShell:

```powershell
python -m pip install -e ".[llm]"
$env:OPENAI_API_KEY = "sk-your-key"
python -m autonomy_score --diff examples\diffs\core-data-migration.diff --llm-analysis
```

Optional settings:

```bash
export AUTONOMY_SCORE_LLM_MODEL="gpt-4.1-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

The repository includes `.env.example`, but the CLI does not load `.env` automatically. That avoids adding another runtime dependency.

## Why Not Google ADK Yet?

Google ADK is useful for larger agentic systems because it supports multi-agent design, workflow agents, tools, runners, sessions, state, and local developer tooling.

This repo does not need that weight yet. The v1 flow is:

1. Deterministic scorer.
2. Optional LLM reviewer.
3. Deterministic renderer/synthesizer.

That keeps the open-source demo focused and easy to run. A future `examples/adk/` workflow would make sense once the project has multiple real agents, such as separate performance, security, architecture, and test reviewers.

Sources:

- [Google ADK overview](https://adk.dev/get-started/about/)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
