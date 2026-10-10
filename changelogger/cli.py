"""Command-line interface for changelogger.

This module provides a minimal CLI that supports ``--help`` and can be
expanded in the future.
"""

import argparse


def main() -> None:
    """Entry point for the ``changelogger`` command.

    The function sets up an :class:`argparse.ArgumentParser` that only
    understands ``--help``.  ``argparse`` automatically handles the help
    flag and exits with status code 0.
    """
    parser = argparse.ArgumentParser(
        prog="changelogger",
        description="Generate Keep a Changelog entries from conventional commit history.",
    )
    # No additional arguments are defined; ``--help`` is handled by argparse.
    parser.parse_args()


if __name__ == "__main__":
    main()
