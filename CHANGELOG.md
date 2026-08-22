# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-21

### Added

- `load_passenv()` — load a password-store namespace into `os.environ`, with
  `override`, `multiline`, `key_transform`, `required`, `verbose` and `store_dir`
  options.
- `passenv_values()` — the same resolution without touching the environment.
- `get_key()` — read a single entry, returning `None` when it does not exist.
- Namespaces: a folder (or a sequence of folders, later overriding earlier);
  recursion into subfolders with the leaf name as the variable name.
- Store-directory resolution: `store_dir` argument, then `$PASSWORD_STORE_DIR`,
  then `~/.password-store`.
- Error hierarchy: `PassEnvError`, `PassNotFoundError`, `PassDecryptError`,
  `NamespaceNotFoundError`, `KeyCollisionError`.
- Key-only logging on the `passenv` logger; secret values are never logged.
- Zero runtime dependencies; `py.typed` ships with the package.

[Unreleased]: https://github.com/dcbark01/python-passenv/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dcbark01/python-passenv/releases/tag/v0.1.0
