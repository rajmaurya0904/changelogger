"""Exceptions that the command line turns into friendly messages."""

from __future__ import annotations


class ChangeloggerError(Exception):
    """Base class for errors that should be shown to the user without a traceback."""


class GitError(ChangeloggerError):
    """git is missing, failed, or was given something it does not understand."""


class NotAGitRepository(GitError):
    """The chosen directory is not inside a git working tree."""


class ConfigError(ChangeloggerError):
    """A --type-map value or similar setting could not be used."""
