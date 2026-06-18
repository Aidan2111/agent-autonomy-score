## Summary

-

## Scope

- [ ] Scoring behavior changed
- [ ] CLI/output behavior changed
- [ ] Docs/examples only
- [ ] CI/release metadata changed

## Validation

- [ ] `python -m unittest discover -s tests`

## Docs and Examples

- [ ] Scoring rule or threshold changes update `docs/scoring/model.md`
- [ ] New or changed fixtures live under `examples/diffs/`, `examples/intents/`, or `examples/complexity/`
- [ ] Architecture or workflow changes update `docs/engineering/architecture.md`, `docs/operations/runbook.md`, or `docs/operations/branching-and-releases.md`

## Security Notes

- [ ] This change does not introduce new secret handling, network egress, or CI permissions.
- [ ] Any LLM-related change keeps deterministic scoring authoritative.
