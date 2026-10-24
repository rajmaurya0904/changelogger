# changelogger

**Turns a git repository's Conventional Commits and version tags into a Keep a Changelog file, for maintainers who would rather not write release notes by hand.**

Release day means scrolling `git log`, deciding which of forty commits a user cares
about, and remembering whether a rename goes under "Changed" or "Removed". The commit
headers already say it: `feat`, `fix`, the `!` that means you broke someone's build.
changelogger reads them, groups them by release tag, and prints the file.

```console
$ changelogger --no-hashes -v
changelogger: skipped 1 non-conventional commit
  29c6d9d Fix typo in readme
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **BREAKING** **cli:** rename --out to --output
  BREAKING CHANGE: scripts passing --out must switch to --output
- **api:** add pagination

### Fixed

- **api:** return 404 for unknown ids ([#9](https://github.com/acme/widget/pull/9))

## [0.1.0] - 2026-01-07

### Added

- read config from pyproject.toml

### Fixed

- **parser:** handle empty input ([#3](https://github.com/acme/widget/pull/3))

[Unreleased]: https://github.com/acme/widget/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/acme/widget/releases/tag/v0.1.0
```

Naming the unreleased commits as the next version, with a custom heading for fixes:

```console
$ changelogger --unreleased --no-header --release 0.2.0 --date 2026-02-10 --no-hashes --no-links --type-map '{"fix": "Bug Fixes"}'
## [0.2.0] - 2026-02-10

### Added

- **BREAKING** **cli:** rename --out to --output
  BREAKING CHANGE: scripts passing --out must switch to --output
- **api:** add pagination

### Bug Fixes

- **api:** return 404 for unknown ids (#9)

```

Outside a repository it says so and exits 1:

```console
$ changelogger /tmp
changelogger: Not a git repository
```

## Install

Not on PyPI yet. Clone the repository, then:

```bash
pip install -e .
```

Needs Python 3.11+ and `git` on PATH. No other dependencies.

## Usage

```bash
changelogger -o CHANGELOG.md                  # the whole history, written to a file
changelogger --since v1.3.0                   # releases after a tag, plus unreleased work
changelogger --unreleased --no-header --release 1.4.0   # just the notes for the next release
changelogger --type-map '{"docs": "Documentation"}'     # rename or reveal sections (null hides)
```

Other flags: `--until REF`, `--date YYYY-MM-DD` (with `--release`), `--no-hashes`,
`--no-links`, `--strict` (exit 2 if any commit is not conventional), `-v` (list the
skipped commits), and an optional first argument for the repository path. Without
`-o` the result goes to stdout. `--type-map` also accepts the path of a JSON file.

Exit codes: 0 success, 1 error (not a repository, unknown tag, bad option), 2 with
`--strict` when non-conventional commits were found. A repository with no usable
commits prints `No conventional commits found` and exits 0.

`SKILL.md` describes the same workflow for Claude Code, so the command can be used as
a skill when the repository is checked out.

## How it works

- Version tags (`v1.2.3` or `1.2.3`, pre-releases included) sorted by semver become
  release blocks. Each holds the commits between that tag and the previous one;
  commits after the newest tag become `[Unreleased]`.
- Each commit header is matched against `type(scope)!: description`. `git revert`'s
  `Revert "..."` messages count as `revert`. A `BREAKING CHANGE:` footer or a `!` marks
  the commit breaking, and its note is printed under the bullet.
- Types map to the six Keep a Changelog headings: `feat` to Added, `fix` to Fixed,
  `perf`/`refactor`/`revert` to Changed, and so on. `docs`, `style`, `test`, `build`,
  `ci` and `chore` are hidden, except when breaking.
- `(#123)` in a description and the commit hash become links when `origin` is an
  ssh, git or https remote on a hosted service; compare links go in the footer.
- `--since`/`--until` accept a version tag. Anything else (a branch, a sha) is treated
  as a plain revision range and printed as one block.
- Commits are read with `git log --no-merges`, so merge commits are not listed.

## Limitations

- It writes a complete file. It does not merge into a CHANGELOG.md you edited by hand;
  use `--unreleased --no-header` and paste, or write to a new file and diff.
- Bullets are the commit descriptions as written. Vague commits give vague notes.
- Commits that are not Conventional Commits are skipped with a count on stderr, not
  guessed at. Only the header and `BREAKING CHANGE:` footers are read.
- Tags on other branches, and tags that are not semver, are ignored or may split the
  history unexpectedly; tags are assumed to lie on one line of history.
- Links assume GitHub-style `/pull/N`, `/commit/SHA` and `/compare/A...B` paths.
- No PyPI release, no `mypy`/strict typing guarantees.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

The tests build real throwaway git repositories, so they need `git` and take about a
minute on Windows.

MIT, see [LICENSE](LICENSE).
