# Case Study: Autonomy Gates for Coding Agents

## Problem

Agentic coding systems can process feedback, edit code, run tests, and open pull requests. The hard part is deciding when that autonomy is appropriate.

Treating every change the same creates two bad outcomes:

- Low-risk changes get slowed down by unnecessary human babysitting.
- High-risk changes get handed to agents before the architecture is clear.

The goal is a practical gate that routes work into the right collaboration mode.

## Hypothesis

Teams can use simple software engineering signals to estimate the supervision level an AI coding agent needs.

The first version does not need to understand the whole codebase. It can still be useful if it identifies obvious risk:

- Algorithmic risk, especially obvious nested iteration.
- State, persistence, auth, billing, and pipeline changes.
- Larger blast radius across files and directories.
- Risky production changes with no tests.
- Presentation-only changes that are usually safe to automate.

## Approach

This repo ships a CLI that reads a unified diff, calculates risk signals, and recommends one of three modes:

- Unsupervised: agent writes code and opens a PR.
- Guided Autonomy: agent proposes architecture, human approves, agent implements.
- Pair Programming: human stays actively in the loop.

The output is designed for humans and automation. It can be read in a terminal, published into a PR summary, or used as a CI threshold.

## Tradeoffs

The scoring model favors transparency over cleverness. A deterministic heuristic is easier for teams to debate, tune, and trust than a hidden model call.

This means it will miss some risks. It will also flag some changes that are safe in a specific codebase. That is acceptable for a first gate because the tool is meant to route work, not make final merge decisions.

## What This Demonstrates

This project is intentionally small, but it shows several production-relevant habits:

- Turning a vague process concern into a runnable developer tool.
- Encoding judgment as a transparent policy.
- Designing for CI and PR workflows.
- Keeping the implementation easy to audit and test.
- Naming where automation should stop and human judgment should start.

## Next Iteration

The strongest next step is calibration against real data:

- Agent-generated PRs that merged cleanly.
- PRs that needed major human correction.
- Rollbacks or incident-linked changes.
- Human review time per risk band.

That feedback loop can turn the current heuristic into a team-specific autonomy policy.
