"""Tests for the commit message parser."""

from changelogger.parser import parse_commit


def test_parse_commit_with_scope():
    """Parse a commit with scope."""
    msg = "feat(core): add parser"
    expected = {"type": "feat", "scope": "core", "description": "add parser"}
    assert parse_commit(msg) == expected


def test_parse_commit_without_scope():
    """Parse a commit without scope."""
    msg = "fix: correct typo"
    expected = {"type": "fix", "scope": None, "description": "correct typo"}
    assert parse_commit(msg) == expected


def test_parse_commit_with_empty_description():
    """Parse a commit with empty description."""
    msg = "feat(core):"
    expected = {"type": "feat", "scope": "core", "description": ""}
    assert parse_commit(msg) == expected


def test_parse_commit_without_colon():
    """Parse a commit without colon (should treat whole as header)."""
    msg = "feat(core)"
    expected = {"type": "feat", "scope": "core", "description": ""}
    assert parse_commit(msg) == expected


def test_parse_commit_without_scope_and_colon():
    """Parse a commit without scope and without colon."""
    msg = "feat"
    expected = {"type": "feat", "scope": None, "description": ""}
    assert parse_commit(msg) == expected