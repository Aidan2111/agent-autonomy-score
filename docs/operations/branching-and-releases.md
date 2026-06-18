# Branching and Releases

This repository uses GitHub Flow because the project is small, public-facing, and CLI-first. Long-lived `develop` or environment branches would add process without improving quality.

## Branching Model

- `main` is the default and releasable branch.
- Work happens on short-lived branches named by intent:
  - `feat/<capability>`
  - `fix/<bug-or-signal>`
  - `docs/<topic>`
  - `chore/<maintenance>`
- Keep unrelated changes on separate branches so review, rollback, and release notes stay clear.
- Merge through pull requests after checks pass.
- Delete merged branches.

## Pull Request Gate

Every pull request should include:

- a short summary of the workflow or scoring behavior being changed
- test evidence, usually `python -m unittest discover -s tests`
- security notes for config, CI permissions, API keys, or LLM behavior
- screenshots or copied CLI output only when output formatting changed

For scoring changes:

- add or update a fixture in `examples/diffs/`, `examples/intents/`, or `examples/complexity/`
- add a test that explains the expected signal or band
- update `docs/scoring/model.md` when a rule, threshold, or known limit changes

## Recommended `main` Protection

Use a GitHub branch protection rule or ruleset so `main` is a protected branch with:

- required pull request before merge
- required status checks: `test` and `score`
- blocked force pushes
- blocked branch deletion
- required conversation resolution
- linear history if the repo standardizes on squash or rebase merges

For a solo-maintained repo, one approving review is useful but optional. The more important guard is that CI passes before `main` changes.

## Release Process

The package version lives in `pyproject.toml`.

1. Update `version` in `pyproject.toml`.
2. Update release notes with user-visible changes.
3. Run:

```bash
uv run --python 3.12 --with-editable . python -m unittest discover -s tests
uv build
```

4. Open a release PR.
5. After merge, tag the release:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

6. Attach built artifacts or publish to PyPI only after the release path is intentionally configured.

## Direct Push Exception

Direct pushes to `main` should be limited to emergency documentation or metadata fixes. If used, run the same local verification commands and follow up with a normal PR if code or scoring policy changed.

## References

- https://docs.github.com/en/get-started/using-github/github-flow
- https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
