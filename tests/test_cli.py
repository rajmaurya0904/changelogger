"""Tests for the CLI entry point."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from changelogger.cli import main


def test_main_help_exits_zero(capsys: pytest.CaptureFixture) -> None:
    """``changelogger --help`` should exit with code 0 and print help."""
    with patch.object(sys, "argv", ["changelogger", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
    assert excinfo.value.code == 0

    # Help text is printed to stdout
    captured = capsys.readouterr()
    assert captured.out
    # Check for typical help content
    assert "usage:" in captured.out.lower()
    assert "changelogger" in captured.out