# Governance

`agent-autonomy-score` is currently maintained by Aidan Marshall under a
lightweight maintainer model.

The maintainer decides what merges and releases. Changes to scoring rules,
signal vocabulary, risk bands, output formats, configuration, or security
boundaries require focused tests and documentation. Deterministic scoring
remains authoritative; optional LLM analysis may advise but must not silently
change the score or supervision mode.

Releases are cut from `main` after the supported Python matrix, package build,
wheel smoke test, and security checks pass. User-visible scoring changes belong
in `CHANGELOG.md` and the scoring documentation.
