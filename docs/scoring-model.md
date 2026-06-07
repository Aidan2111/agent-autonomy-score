# Scoring Model

Agent Autonomy Score starts at 1 and adds points for risk signals found in a unified diff. The final score is capped between 1 and 10.

## Bands

| Score | Band | Recommended mode |
| --- | --- | --- |
| 1-3 | Low Risk | Unsupervised |
| 4-7 | Medium Risk | Guided Autonomy |
| 8-10 | High Risk | Pair Programming |

## Signals

| Signal | Points | Why it matters |
| --- | ---: | --- |
| `blast-radius:file-count` | +1 or +2 | More files increases review and integration risk. |
| `blast-radius:added-lines` | +1 or +2 | Large patches are harder for agents and humans to validate. |
| `state-or-persistence` | +2 | State, storage, auth, and pipelines have larger failure modes than presentation code. |
| `critical-content` | +2 | Migration, transaction, auth, concurrency, and destructive terms deserve stricter oversight. |
| `algorithmic-risk` | +1 | Algorithms and data-flow changes can hide complexity or performance regressions. |
| `big-o:nested-loop` | +2 | Nested iteration is a simple proxy for O(N^2) risk. |
| `blast-radius:directory-spread` | +1 | A cross-cutting change often needs architectural context. |
| `validation:no-tests-in-diff` | +1 | Risky production changes without tests should not be fully trusted. |
| `presentation-only-cap` | 0 | Presentation-only changes are capped at low risk unless stronger signals appear. |

## Calibration

The default model is conservative, but not universal. Adjust it by team and domain:

- Regulated or financial systems may lower the allowed autonomy threshold.
- Internal tools may tolerate more unsupervised UI and workflow changes.
- Mobile apps may treat persistence, keychain, sync, and migration code as high risk.
- AI-heavy products may add terms for prompt policy, evaluation, retrieval, and tool execution.

## Known Limits

The scorer does not build an AST and does not prove computational complexity. It uses path and content heuristics to decide when a human should take a closer look.

That is deliberate for v0.1. A clear heuristic is easier to tune than a magical score nobody can explain.

## LLM Advisory Layer

When `--llm-analysis` is enabled, the deterministic score still owns the final recommendation. The model receives the diff and deterministic result, then returns structured advisory fields.

Use this when a reviewer wants a second opinion on:

- risks not represented by the heuristic terms
- signals that may be false positives
- the next human action before giving an agent more autonomy

Do not use the LLM layer as the merge gate by itself.
