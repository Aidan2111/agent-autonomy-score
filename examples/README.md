# Examples

Fixtures are grouped by what they demonstrate.

## `diffs/`

Representative pull request diffs for normal scoring:

- `swiftui-copy-change.diff`: low-risk presentation change
- `api-cache-refactor.diff`: medium-risk cache/data-flow change
- `core-data-migration.diff`: high-risk persistence migration

## `intents/`

Pre-work task briefs for intent scoring:

- `intent-swiftui-copy.txt`
- `intent-api-cache-refactor.txt`
- `intent-core-data-migration.txt`

## `complexity/`

Boundary cases for the complexity-risk heuristic:

- `nested-loop.diff`: visible nested iteration
- `recursion-limit.diff`: recursive work that needs human interpretation
- `library-call-limit.diff`: hidden complexity behind library calls

These examples document limits as much as happy paths. The scorer is a review-routing heuristic, not an exact Big-O analyzer.
