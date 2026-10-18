"""Parse Conventional Commits messages.

Two entry points:

* :func:`parse_message` is the strict parser the changelog builder uses. It returns
  ``None`` for anything that is not a conventional commit.
* :func:`parse_commit` is the older, lenient header splitter that always returns a
  four-key dictionary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADER = re.compile(
    r"^(?P<type>[A-Za-z]+)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<bang>!)?"
    r":[ ](?P<description>\S.*)$"
)
_REVERT = re.compile(r'^Revert "(?P<subject>.+)"$')
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ?(?P<text>.*)$")
_ANY_FOOTER = re.compile(r"^(?:[A-Za-z][A-Za-z-]*|BREAKING CHANGE)(?:: | #)")


@dataclass(frozen=True)
class ParsedMessage:
    """A commit message split into its conventional parts."""

    type: str
    description: str
    scope: str | None = None
    breaking: bool = False
    breaking_notes: tuple[str, ...] = field(default_factory=tuple)
    body: str = ""


def _breaking_notes(lines: list[str]) -> list[str]:
    """Text of every ``BREAKING CHANGE:`` footer, with continuation lines joined."""
    notes: list[str] = []
    i = 0
    while i < len(lines):
        m = _BREAKING_FOOTER.match(lines[i])
        i += 1
        if not m:
            continue
        parts = [m.group("text").strip()]
        while i < len(lines) and lines[i].strip() and not _ANY_FOOTER.match(lines[i]):
            parts.append(lines[i].strip())
            i += 1
        notes.append(" ".join(p for p in parts if p))
    return notes


def parse_message(message: str) -> ParsedMessage | None:
    """Parse a full commit message, or return ``None`` if it is not conventional.

    The header must look like ``type(scope)!: description``; the scope and the ``!``
    are optional. A ``BREAKING CHANGE:`` (or ``BREAKING-CHANGE:``) footer at the
    start of a line also marks the commit as breaking, and its text is kept.
    ``Revert "..."`` messages written by ``git revert`` are read as ``revert``.
    """
    lines = message.replace("\r\n", "\n").strip().split("\n")
    header = lines[0].strip()
    body_lines = lines[1:]
    body = "\n".join(body_lines).strip()

    revert = _REVERT.match(header)
    if revert:
        notes = _breaking_notes(body_lines)
        return ParsedMessage(
            "revert", revert.group("subject").strip(), None, bool(notes), tuple(notes), body
        )

    m = _HEADER.match(header)
    if not m:
        return None
    notes = _breaking_notes(body_lines)
    scope = m.group("scope")
    return ParsedMessage(
        type=m.group("type").lower(),
        description=m.group("description").strip(),
        scope=scope.strip() if scope and scope.strip() else None,
        breaking=bool(m.group("bang")) or bool(notes),
        breaking_notes=tuple(notes),
        body=body,
    )


def parse_commit(message: str) -> dict:
    """Leniently split a commit header into ``type``, ``scope``, ``description``, ``breaking``.

    Unlike :func:`parse_message` this never rejects input: a message without ``": "``
    is treated as a bare header with an empty description. ``breaking`` is set by a
    trailing ``!`` on the header or by a ``BREAKING CHANGE:`` footer at the start of
    a line.
    """
    result = {"type": None, "scope": None, "description": None, "breaking": False}

    first_line, _, rest = message.partition("\n")
    if ": " not in first_line:
        header = first_line.strip()
        description = ""
    else:
        header, description = first_line.split(": ", 1)

    if header.endswith("!"):
        result["breaking"] = True
        header = header[:-1]

    if "(" in header and ")" in header:
        type_end = header.find("(")
        scope_start = type_end + 1
        scope_end = header.find(")", scope_start)
        result["type"] = header[:type_end]
        result["scope"] = header[scope_start:scope_end]
    else:
        result["type"] = header
        result["scope"] = None

    result["description"] = description.strip()

    if _breaking_notes(rest.split("\n")):
        result["breaking"] = True

    return result
