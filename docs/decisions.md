# Engineering Decisions

## Use a CLI first

A CLI is the smallest useful surface for local development, CI, and pull request automation. It also keeps the project easy to inspect during a portfolio review.

## Parse diffs instead of repositories

The first version scores changed lines and changed paths. That makes it fast, deterministic, and easy to run in CI without indexing an entire codebase.

Future versions can add optional repository-aware analyzers.

## Keep the model deterministic

The score should be explainable. A team should be able to point to each signal and decide whether it matches their engineering risk tolerance.

LLM-based explanation can be layered on later, but the routing decision should not require an LLM call.

## Prefer configuration over hardcoded company policy

The default terms encode a generic SDLC view of risk. Teams should tune path and content terms to match their architecture.

Examples:

- `CoreData`, `Migrations`, and `SyncEngine` for iOS.
- `payments`, `ledger`, and `entitlements` for SaaS billing.
- `retrieval`, `tools`, and `evals` for AI systems.

