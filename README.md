# python-passenv

Load environment variables from the [`pass`](https://www.passwordstore.org/) password
store, with the ergonomics of [`python-dotenv`](https://github.com/theskumar/python-dotenv).

One pass entry is one environment variable. Folders are namespaces.

```text
~/.password-store/
├── shared/
│   └── webhook_url.gpg      →  WEBHOOK_URL
└── project_a/
    ├── api_token.gpg         →  API_TOKEN
    └── db/
        └── dsn.gpg           →  DSN
```

- No `.env` file on disk — secrets stay encrypted until the process asks for them.
- Zero runtime dependencies; it shells out to the `pass` binary you already trust.
- Fully typed (`py.typed`), Python 3.10+.

## Install

```bash
uv add python-passenv     # or: pip install python-passenv
```

You need `pass` on your `PATH` and a store you can decrypt.

## Quickstart

```python
from passenv import load_passenv

load_passenv("project_a")   # decrypts project_a/** into os.environ, returns True

import os
os.environ["API_TOKEN"]     # → 's3cret…'
```

Read the values without touching the process environment:

```python
from passenv import passenv_values

config = passenv_values("project_a")     # {'API_TOKEN': 's3cret…', 'DSN': 'postgres…'}
```

Read a single entry by its full path:

```python
from passenv import get_key

get_key("project_a/api_token")           # → 's3cret…'
get_key("project_a/nope")                # → None
```

## Coming from python-dotenv

| `python-dotenv` | `python-passenv` |
| --- | --- |
| `load_dotenv()` | `load_passenv()` |
| `load_dotenv(".env.prod")` | `load_passenv("prod")` |
| `load_dotenv(override=True)` | `load_passenv(override=True)` |
| `dotenv_values()` | `passenv_values()` |
| `get_key(".env", "API_TOKEN")` | `get_key("project_a/api_token")` |
| `set_key` / `unset_key` | not in v1 — use the `pass` CLI |
| `$VAR` interpolation | not in v1 |
| source: a file path | source: a store namespace |

## Namespace semantics

A namespace is a folder path relative to the store root.

```python
load_passenv()                          # the whole store
load_passenv("project_a")               # project_a/** only
load_passenv(["shared", "project_a"])   # merged; project_a wins on conflicts
```

- **Recursive.** `project_a/db/dsn` is included in `load_passenv("project_a")`.
- **Leaf names only.** That entry becomes `DSN`, not `DB_DSN`.
- **Collisions are errors.** Two entries in one namespace whose leaves map to the same
  variable raise `KeyCollisionError` — detected before anything is decrypted.
- **Layering across namespaces is fine.** Later namespaces override earlier ones, and
  the merge is resolved *before* anything is written to `os.environ`.
- **Environment assignments are validated first.** `load_passenv` rejects empty names,
  names containing `=` or null bytes, and values containing null bytes with `PassEnvError`
  before writing any variables. `passenv_values` still returns an ordinary dictionary.
- **Only `*.gpg` files count.** Dotfiles and dot-directories (`.git`, `.gpg-id`,
  `.extensions`) are skipped.

## Values

By default a variable gets the **first line** of the entry — the `pass` convention of
"password on line one, metadata below":

```text
s3cret-token-value
url: https://api.example.com
user: service-account
```

```python
passenv_values("project_a")["API_TOKEN"]                 # 's3cret-token-value'
passenv_values("project_a", multiline=True)["API_TOKEN"] # the whole entry, one trailing \n removed
```

Values are never `.strip()`ed — leading and trailing spaces in a secret survive intact.

## Naming

`key_transform` is applied to the leaf name and defaults to `str.upper`:

```python
load_passenv("project_a", key_transform=lambda leaf: f"APP_{leaf.upper()}")  # APP_API_TOKEN, …
```

## Where the store lives

In precedence order:

1. the `store_dir=` argument,
2. `$PASSWORD_STORE_DIR`,
3. `~/.password-store`.

When `store_dir` is given it is exported as `PASSWORD_STORE_DIR` to the `pass`
subprocess, so a non-default store works without touching your own environment.

## Errors

| Exception | Raised when |
| --- | --- |
| `PassEnvError` | base class for everything below |
| `PassNotFoundError` | the `pass` executable is not on `PATH` |
| `PassDecryptError` | `pass show` exited non-zero (`.entry`, `.returncode`, `.stderr`) |
| `NamespaceNotFoundError` | the namespace folder is missing **and** `required=True` |
| `KeyCollisionError` | two entries map to the same variable (`.key`, `.entries`) |

With `required=False` (the default) a missing namespace is not an error:
`load_passenv` returns `False` and `passenv_values` returns `{}`.

## Logging

`passenv` logs to the `passenv` logger and records **keys only, never values**.
`load_passenv(verbose=True)` turns those records on even if your app has not
configured logging.

## API

```python
def load_passenv(namespace=None, *, override=False, multiline=False,
                 key_transform=str.upper, required=False, verbose=False,
                 store_dir=None) -> bool: ...

def passenv_values(namespace=None, *, multiline=False, key_transform=str.upper,
                   required=False, store_dir=None) -> dict[str, str]: ...

def get_key(entry, *, multiline=False, store_dir=None) -> str | None: ...
```

`load_passenv` returns `True` if at least one entry was read. With `override=False`
it never clobbers a variable that is already set.

## Development

```bash
uv sync --group dev
uv run prek install           # install the pre-commit and commit-msg hooks (once per clone)
uv run ruff check . && uv run ruff format --check . && uv run pyrefly check
uv run pytest                 # unit tests, no gpg required
uv run pytest -m integration  # real pass + gpg, ephemeral key and store
```

The integration suite generates an unprotected GPG key into a temporary `GNUPGHOME`,
runs `pass init` against a temporary store, and is skipped when `pass` or `gpg` is
missing. It never touches your real store.

### Git hooks

[`prek`](https://prek.j178.dev) runs the checks in [`prek.toml`](prek.toml) before every
commit. Because this project's whole subject is secrets, the secret-scanning hooks run
first and abort the commit immediately when one of them trips:

| Hook | Blocks |
| --- | --- |
| `betterleaks` | credentials in the staged diff, matched against betterleaks' provider rules |
| `detect-private-key` | PEM/OpenSSH private-key blocks |
| `deny-filename-pattern` | `*.gpg`, `*.pem`, `*.key`, `.env*`, `id_rsa`, `.netrc`, … |
| `deny-filename-pattern` (store paths) | anything under a `.password-store/` or `.gnupg/` directory |

The rest of the run is repo hygiene (trailing whitespace, line endings, TOML/YAML
syntax, large files) followed by `ruff check --fix`, `ruff format` and `pyrefly check`,
all invoked through `uv run` so hook and CI versions come from the same dev group.

```bash
uv run prek run --all-files   # run every hook by hand
uv run prek run betterleaks   # run just one
uv run prek auto-update       # bump pinned hook revisions
```

CI runs the same hooks via `prek run --all-files`. Since the `betterleaks` hook only
inspects staged changes, a separate CI job scans the full history with the pinned
betterleaks image.

### Commit messages

Commit subjects follow [Conventional Commits](https://www.conventionalcommits.org/),
because the release version is computed from them — `feat:` bumps the minor, `fix:` and
`perf:` bump the patch, everything else releases nothing. A `commit-msg` hook rejects
subjects that do not parse. See [RELEASING.md](RELEASING.md).

## Releasing

Merging to `main` is the release. python-semantic-release reads the commits since the
last tag, bumps the version, writes the changelog, tags, cuts a GitHub Release with the
sdist and wheel attached, and publishes to PyPI via Trusted Publishing — or does nothing
at all, if nothing releasable landed. Details, including the dry-run and forced-bump
triggers, are in [RELEASING.md](RELEASING.md).

## License

MIT — see [LICENSE](LICENSE).
