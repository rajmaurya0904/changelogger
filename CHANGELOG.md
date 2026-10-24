# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- `changelogger` command that reads git history and prints a Keep a Changelog file.
- Conventional Commits parser with scopes, `!` markers and `BREAKING CHANGE:` footers.
- Release blocks built from semver tags, with `Unreleased` for newer commits.
- `--since`, `--until`, `--release`, `--date`, `--unreleased`, `--type-map`, `-o`,
  `--no-hashes`, `--no-links`, `--no-header` and `--strict`.
- Commit, pull request and compare links for ssh, git and https remotes.
- Claude Code skill instructions in `SKILL.md`.
