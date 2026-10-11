---
name: changelogger
description: Claude Code skill that generates Keep a Changelog entries from conventional commit history, simplifying release notes for developers.
---

# Changelogger

Stub. This skill has no instructions yet.

Only `changelogger.parser.parse_commit()` is implemented; it splits a Conventional
Commits header into `type`, `scope`, `description` and `breaking`. Nothing reads git
history or writes a changelog. See README.md for what does and does not work.
