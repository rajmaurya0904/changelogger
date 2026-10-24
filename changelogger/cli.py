"""Command-line interface: ``changelogger [path] [options]``."""

from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from pathlib import Path

from . import __version__
from .builder import build_changelog
from .config import parse_type_map
from .errors import ChangeloggerError
from .generate import collect
from .gitlog import ensure_repository, remote_url

EPILOG = (
    "Exit codes: 0 ok, 1 error (not a git repository, unknown ref, bad option), "
    "2 non-conventional commits found while --strict is set."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="changelogger",
        description="Generate a Keep a Changelog file from conventional commit history.",
        epilog=EPILOG,
    )
    p.add_argument("path", nargs="?", default=".", help="repository directory (default: .)")
    p.add_argument("--since", metavar="REF", help="releases after this tag, or commits after REF")
    p.add_argument("--until", metavar="REF", help="releases up to this tag, or commits up to REF")
    p.add_argument(
        "--type-map",
        metavar="JSON|FILE",
        help='override headings, e.g. {"fix": "Bug Fixes"}; a null value hides that type',
    )
    p.add_argument("--release", metavar="VERSION", help="name the unreleased commits VERSION")
    p.add_argument("--date", metavar="YYYY-MM-DD", help="date for --release (default: today)")
    p.add_argument("--unreleased", action="store_true", help="print only the newest block")
    p.add_argument("-o", "--output", metavar="FILE", help="write to FILE instead of stdout")
    p.add_argument("--no-hashes", action="store_true", help="omit commit hashes")
    p.add_argument("--no-links", action="store_true", help="omit commit, PR and compare links")
    p.add_argument("--strict", action="store_true", help="exit 2 if any commit is not conventional")
    p.add_argument("-v", "--verbose", action="store_true", help="list skipped commits on stderr")
    p.add_argument("--version", action="version", version=f"changelogger {__version__}")
    return p


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def run(args: argparse.Namespace) -> int:
    type_map = parse_type_map(args.type_map) if args.type_map else None
    if args.date and not args.release:
        raise ChangeloggerError("--date only makes sense together with --release")
    if args.date:
        try:
            _date.fromisoformat(args.date)
        except ValueError:
            msg = f"--date must look like 2026-01-31, got {args.date!r}"
            raise ChangeloggerError(msg) from None

    repo = ensure_repository(Path(args.path))
    collected = collect(repo, args.since, args.until)

    if args.release:
        newest = collected.releases[0] if collected.releases else None
        if newest is None or newest.version is not None:
            raise ChangeloggerError("--release needs unreleased commits, but there are none")
        newest.version = args.release.lstrip("vV")
        newest.date = args.date or _date.today().isoformat()

    releases = collected.releases[:1] if args.unreleased else collected.releases
    strict_code = 2 if args.strict and collected.skipped else 0

    if collected.skipped:
        n = len(collected.skipped)
        print(f"changelogger: skipped {_plural(n, 'non-conventional commit')}", file=sys.stderr)
        if args.verbose:
            for c in collected.skipped:
                print(f"  {c.sha[:7]} {c.message.splitlines()[0][:70]}", file=sys.stderr)

    if collected.entry_count == 0:
        print("No conventional commits found")
        return strict_code

    url = None if args.no_links else remote_url(repo)
    text = build_changelog(releases, type_map, url, hashes=not args.no_hashes)
    if "\n## [" not in text:
        print("No user-facing changes: every commit in range has a hidden type")
        return strict_code
    if args.output:
        out = Path(args.output)
        try:
            out.write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            raise ChangeloggerError(f"cannot write {out}: {exc.strerror or exc}") from None
        print(f"Wrote {out} ({_plural(len(releases), 'release block')})", file=sys.stderr)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    return strict_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except ChangeloggerError as exc:
        print(f"changelogger: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        return 130
