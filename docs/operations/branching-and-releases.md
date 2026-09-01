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

6. Pushing a matching `vX.Y.Z` tag runs `.github/workflows/release.yml`, repeats
   the tests and distribution checks, and creates a GitHub release with the
   wheel and source archive attached.
7. Publish to PyPI only after trusted publishing is configured for this
   repository and the package name. PyPI publication is intentionally separate
   from the GitHub release until that one-time external configuration exists.

### PyPI trusted publishing

`.github/workflows/publish-pypi.yml` is deliberately manual. It accepts a tag,
checks that the checkout is exactly at that tag, verifies that the tag matches
the version in `pyproject.toml`, runs the tests, rebuilds the distributions, and
uses OpenID Connect to publish them. It has no push, tag, or release trigger.

Before the first publication, a maintainer must create the project (or pending
publisher) on PyPI and register this repository, the `publish-pypi.yml`
workflow, and the `pypi` environment as a trusted publisher. No long-lived API
token belongs in GitHub secrets. After that one-time setup, dispatch **Publish
to PyPI** with an existing release tag such as `v0.2.0`.

Treat the GitHub release as the source of truth until the first PyPI workflow
finishes successfully. Do not add a PyPI badge or `pip install
agent-autonomy-score` instructions before then.

## Direct Push Exception

Direct pushes to `main` should be limited to emergency documentation or metadata fixes. If used, run the same local verification commands and follow up with a normal PR if code or scoring policy changed.

## References

- https://docs.github.com/en/get-started/using-github/github-flow
- https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
