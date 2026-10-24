---
name: changelogger
description: Generate or refresh a Keep a Changelog CHANGELOG.md, or draft release notes, from a repository's conventional commit history. Use when the user asks for a changelog, release notes, "what changed since vX", or is about to cut a release.
---

# changelogger

This skill drives the `changelogger` command, which reads `git log` and the semver
tags of a repository and prints Keep a Changelog markdown. It needs git on PATH and
the package installed (`pip install -e .` from a clone of this repository).

## When to use it

- The user wants a CHANGELOG.md created or regenerated.
- The user wants release notes for the next version, or for everything since a tag.
- The user asks which commits will not make it into the changelog.

## Steps

1. Confirm the target is a git repository and check for version tags with
   `git tag --list "v*"`. Tags such as `v1.2.0` or `1.2.0` become release headings;
   commits after the newest tag become `[Unreleased]`.
2. Preview without writing anything: `changelogger <path> -v`. Warnings on stderr list
   commits that are not Conventional Commits and were skipped. Report these to the
   user rather than guessing a type for them.
3. Pick the form that matches the request:
   - Whole file: `changelogger -o CHANGELOG.md`
   - Notes for the coming release only:
     `changelogger --unreleased --no-header --release 1.4.0`
   - Everything after a tag: `changelogger --since v1.3.0`
   - Different headings:
     `changelogger --type-map '{"fix": "Bug Fixes", "docs": "Documentation"}'`
     (a `null` value hides a type).
4. Read the output before handing it over. Entries are the commit descriptions
   verbatim, so a vague commit gives a vague bullet. Suggest rewording specific lines
   but do not silently rewrite them.
5. Writing with `-o` replaces the target file entirely. If the user keeps hand-written
   notes in CHANGELOG.md, write to a new file and let them merge, or use
   `--unreleased --no-header` and paste the block in.

## Exit codes

0 success (also when no conventional commits exist, which prints a message), 1 for
errors such as a missing repository or unknown tag, 2 when `--strict` is set and some
commits were not conventional.

## Limits to mention

Only the commit header and `BREAKING CHANGE:` footers are read. Types `docs`, `style`,
`test`, `build`, `ci` and `chore` are hidden unless the type map shows them, except
that a breaking commit is always listed. Merge commits are ignored. Compare and PR
links are generated only when `origin` points at a hosted repository.
