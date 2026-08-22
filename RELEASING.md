# Releasing

Versions are not chosen by hand. Every push to `main` runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which asks
[python-semantic-release](https://python-semantic-release.readthedocs.io/) what the
[Conventional Commits](https://www.conventionalcommits.org/) since the last tag add up
to. If they add up to nothing, the run is a no-op.

## What a commit does to the version

| Commit subject | Bump | In the changelog |
| --- | --- | --- |
| `feat: …` | minor (`0.1.0` → `0.2.0`) | Features |
| `fix: …` | patch (`0.1.0` → `0.1.1`) | Bug Fixes |
| `perf: …` | patch | Performance Improvements |
| `feat!: …`, or a `BREAKING CHANGE:` footer | see below | Breaking Changes |
| `build:` `chore:` `ci:` `docs:` `refactor:` `style:` `test:` | none | listed, no release |
| anything else | none | not listed at all |

A scope is optional and free-form: `fix(store): …`.

**While the package is `0.x`, a breaking change bumps the minor, not the major** —
`major_on_zero = false` in `pyproject.toml`. Releasing `1.0.0` is a deliberate act: set
`allow_zero_version = false`, or force it once from the Actions tab.

The `commit-msg` hook in [`prek.toml`](prek.toml) rejects subjects that do not parse, so
a change cannot quietly fall out of the changelog. It accepts exactly the types above,
plus git's own `Merge …` / `Revert …` / `fixup!` / `squash!` wording.

Pull requests are squash-merged, so **the squash subject is the commit that counts** —
the one typed into the GitHub merge box, not the branch's individual commits. The parser
also reads Conventional Commits out of a squashed body (`parse_squash_commits = true`),
so listing them there works too.

## What the workflow does

1. **verify** — the same hooks, unit tests and artifact build that ran on the pull
   request, one last time before anything becomes permanent.
2. **release** — works out the next version, rewrites `version` in `pyproject.toml` and
   `__version__` in `src/passenv/__init__.py`, prepends the changelog entry, commits as
   `chore(release): vX.Y.Z`, tags it, and cuts a GitHub Release.
3. **artifacts** — checks out that tag, builds the sdist and wheel with `uv build`, runs
   `twine check --strict`, refuses to continue if the built version is not the released
   one, and attaches both files to the GitHub Release.
4. **publish** — uploads the same two files to PyPI.

Each step gates the next, and the workflow is excluded from `cancel-in-progress` so a
release is never killed between the tag and the upload. The artifacts are built from the
tag rather than inside the release action's container, so what reaches PyPI is built by
the same `uv` that the test matrix uses.

## Publishing credentials

There are none. PyPI uses [Trusted
Publishing](https://docs.pypi.org/trusted-publishers/): it verifies the workflow's OIDC
identity instead of a stored token. The publisher registered on PyPI must match:

| Field | Value |
| --- | --- |
| Owner | `dcbark01` |
| Repository | `python-passenv` |
| Workflow | `release.yml` |
| Environment | `pypi` |

Changing the workflow's filename or its `environment:` name breaks publishing until the
PyPI side is updated to match.

## Running it by hand

The **Release** workflow has a `workflow_dispatch` trigger with three inputs:

- **dry_run** — report the version that would be cut and stop. Nothing is committed,
  tagged, released or published. Use this to sanity-check the commit history.
- **force** — `patch` / `minor` / `major`, overriding what the commits imply. This is how
  the first release is cut, and how `1.0.0` is declared.
- **prerelease** — cut `X.Y.Z-rc.N` instead of a final version.

Locally, without touching the remote:

```bash
uv run --group release semantic-release --noop version --print   # next version
uv run --group release semantic-release --noop changelog         # rendered changelog
```
