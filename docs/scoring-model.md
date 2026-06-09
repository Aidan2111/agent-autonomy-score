# Scoring Model

Agent Autonomy Score starts at 1 and adds points for risk signals. The final score is capped between 1 and 10.

There are three scoring modes:

- Intent scoring: pre-work risk prediction from a feature request, bug report, or task brief.
- Diff scoring: post-work verification from a unified diff.
- Gate scoring: combines intent and diff results; the higher score wins.

This matters because a diff only exists after work is done. Intent scoring decides how much autonomy an agent should get before implementation. Diff scoring checks whether the completed work stayed inside that autonomy envelope.

## Bands

| Score | Band | Recommended mode |
| --- | --- | --- |
| 1-3 | Low Risk | Unsupervised |
| 4-7 | Medium Risk | Guided Autonomy |
| 8-10 | High Risk | Pair Programming |

## Diff Signals

| Signal | Points | Why it matters |
| --- | ---: | --- |
| `blast-radius:file-count` | +1 or +2 | More files increases review and integration risk. |
| `blast-radius:added-lines` | +1 or +2 | Large patches are harder for agents and humans to validate. |
| `state-or-persistence` | +2 | State, storage, auth, and pipelines have larger failure modes than presentation code. |
| `critical-content` | +2 | Migration, transaction, auth, concurrency, and destructive terms deserve stricter oversight. |
| `algorithmic-risk` | +1 | Algorithms and data-flow changes can hide complexity or performance regressions. |
| `big-o:nested-loop` | +2 | Nested iteration is a simple proxy for complexity risk, not a proof of exact Big-O. |
| `blast-radius:directory-spread` | +1 | A cross-cutting change often needs architectural context. |
| `validation:no-tests-in-diff` | +1 | Risky production changes without tests should not be fully trusted. |
| `presentation-only-cap` | 0 | Presentation-only changes are capped at low risk unless stronger signals appear. |

## Intent Signals

| Signal | Points | Why it matters |
| --- | ---: | --- |
| `intent:critical-domain` | +3 | Security, production data, migrations, billing, destructive work, and concurrency need early human judgment. |
| `intent:state-or-persistence` | +2 | State, storage, auth, cache, sync, and pipeline behavior usually carry larger failure modes than UI polish. |
| `intent:algorithmic-risk` | +1 | Algorithmic and data-flow requests can hide complexity or performance risks. |
| `intent:blast-radius` | +2 | Architecture, global, shared, core, or cross-cutting language implies broader impact. |
| `intent:scope-unclear` | +3 | Vague requests without concrete files or components should start in guided autonomy. |
| `intent:large-request` | +1 or +2 | Long task briefs often contain multiple behaviors or acceptance criteria. |
| `intent:validation-not-mentioned` | +1 | Risky requests should mention tests, validation, or evaluation before autonomy increases. |
| `intent:presentation-only-cap` | 0 | Copy, style, spacing, and simple UI surface work are capped at low risk unless stronger signals appear. |

## Gate Rule

When both an intent and a diff are provided, the final gate score is:

```text
max(intent_score, diff_score)
```

The higher risk wins because the two passes answer different questions:

- Intent score: "How much supervision should the agent have before writing code?"
- Diff score: "How much review does the actual implementation need before merge?"

Examples:

| Intent | Diff | Gate | Interpretation |
| ---: | ---: | ---: | --- |
| 2 | 2 | 2 | Low-risk task stayed low-risk. |
| 2 | 8 | 8 | Agent likely wandered into risky implementation territory. |
| 8 | 3 | 8 | Original task was sensitive even if the patch looks small. |
| 6 | 6 | 6 | Intent and implementation agree on guided autonomy. |

## Calibration

The default model is conservative, but not universal. Adjust it by team and domain:

- Regulated or financial systems may lower the allowed autonomy threshold.
- Internal tools may tolerate more unsupervised UI and workflow changes.
- Mobile apps may treat persistence, keychain, sync, and migration code as high risk.
- AI-heavy products may add terms for prompt policy, evaluation, retrieval, and tool execution.

When using a custom config in CI, load it from a protected source. A pull request should not be able to weaken the scoring policy used to evaluate that same pull request.

## Known Complexity Limits

The scorer does not build an AST and does not determine exact Big-O. It uses path, content, and task-language heuristics to decide when a human should take a closer look.

That is deliberate for v0.1. A clear heuristic is easier to tune than a magical score nobody can explain.

Cases that need human interpretation:

- recursion can encode linear, logarithmic, exponential, or tree-shaped work without adding a visible loop.
- divide-and-conquer code, such as merge sort, can look locally linear while doing O(n log n) work across recursive levels.
- amortized data structures can make one operation look risky or cheap without the surrounding usage pattern.
- library calls such as sorting, grouping, query builders, or framework helpers can hide complexity behind one line.

The goal is to flag common complexity patterns and obvious regressions, not to replace algorithm analysis.

## LLM Advisory Layer

When `--llm-analysis` is enabled, the deterministic score still owns the final recommendation. The model receives the diff and deterministic result, then returns structured advisory fields.

Use this when a reviewer wants a second opinion on:

- risks not represented by the heuristic terms
- signals that may be false positives
- the next human action before giving an agent more autonomy

Do not use the LLM layer as the merge gate by itself.
