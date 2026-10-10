"""Smoke test: package imports cleanly. Replace/extend as modules land."""

import changelogger


def test_version_is_set() -> None:
    assert changelogger.__version__
