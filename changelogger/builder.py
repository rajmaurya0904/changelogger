"""Turn parsed commits into Keep a Changelog markdown."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .config import BREAKING_FALLBACK_SECTION, resolve_type_map, section_order
from .parser import ParsedMessage

HEADER = """\
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""

_PR_REF = re.compile(r"\(#(\d+)\)")


@dataclass(frozen=True)
class Entry:
    """One commit, ready to be placed in a section."""

    type: str
    description: str
    scope: str | None = None
    breaking: bool = False
    breaking_notes: tuple[str, ...] = ()
    sha: str = ""


@dataclass
class Release:
    """A block of the changelog. ``version`` is ``None`` for Unreleased."""

    version: str | None
    date: str | None = None
    entries: list[Entry] = field(default_factory=list)
    tag: str | None = None  # the git tag this release was cut from, used for compare links


def entry_from(item: Entry | ParsedMessage | Mapping[str, Any], sha: str = "") -> Entry:
    """Coerce a parsed message or a plain dict into an :class:`Entry`."""
    if isinstance(item, Entry):
        return item
    if isinstance(item, ParsedMessage):
        return Entry(
            item.type, item.description, item.scope, item.breaking, item.breaking_notes, sha
        )
    return Entry(
        type=str(item.get("type") or "").lower(),
        description=str(item.get("description") or ""),
        scope=item.get("scope") or None,
        breaking=bool(item.get("breaking", False)),
        breaking_notes=tuple(item.get("breaking_notes", ())),
        sha=str(item.get("sha") or sha),
    )


def heading_for(entry: Entry, type_map: Mapping[str, str | None]) -> str | None:
    """Section an entry belongs in, or ``None`` if its type is hidden.

    Breaking changes are never hidden: they fall back to ``Changed``.
    """
    heading = type_map.get(entry.type)
    if heading:
        return heading
    return BREAKING_FALLBACK_SECTION if entry.breaking else None


def group_entries(
    entries: Iterable[Entry], type_map: Mapping[str, str | None]
) -> tuple[dict[str, list[Entry]], list[Entry]]:
    """Split entries into ``{heading: [entries]}`` (in print order) and the hidden ones."""
    buckets: dict[str, list[Entry]] = {}
    hidden: list[Entry] = []
    for e in entries:
        heading = heading_for(e, type_map)
        if heading is None:
            hidden.append(e)
        else:
            buckets.setdefault(heading, []).append(e)
    ordered = {h: buckets[h] for h in section_order(dict(type_map)) if h in buckets}
    return ordered, hidden


def _linkify(text: str, repo_url: str | None) -> str:
    if not repo_url:
        return text
    return _PR_REF.sub(lambda m: f"([#{m.group(1)}]({repo_url}/pull/{m.group(1)}))", text)


def render_entry(entry: Entry, repo_url: str | None = None, hashes: bool = True) -> str:
    """One bullet (plus an indented note line per ``BREAKING CHANGE`` footer)."""
    parts: list[str] = []
    if entry.breaking:
        parts.append("**BREAKING**")
    if entry.scope:
        parts.append(f"**{entry.scope}:**")
    parts.append(_linkify(entry.description, repo_url))
    line = "- " + " ".join(parts)
    if hashes and entry.sha:
        short = entry.sha[:7]
        line += f" ([{short}]({repo_url}/commit/{entry.sha}))" if repo_url else f" ({short})"
    for note in entry.breaking_notes:
        if note and note != entry.description:
            line += f"\n  BREAKING CHANGE: {note}"
    return line


def heading_line(release: Release) -> str:
    """``## [Unreleased]`` or ``## [1.2.0] - 2026-01-31``."""
    if release.version is None:
        return "## [Unreleased]"
    line = f"## [{release.version}]"
    return f"{line} - {release.date}" if release.date else line


def build_section(
    commits: Iterable[Entry | ParsedMessage | Mapping[str, Any]],
    version: str | None = None,
    date: str | None = None,
    type_map: Mapping[str, str | None] | None = None,
    repo_url: str | None = None,
    hashes: bool = True,
) -> str:
    """Markdown for one release block, grouped under Keep a Changelog headings.

    ``commits`` may be :class:`Entry` objects, parsed messages, or dicts with at least
    ``type`` and ``description``. Newest-first input stays newest-first within a section.
    """
    merged = resolve_type_map(dict(type_map) if type_map else None)
    entries = [entry_from(c) for c in commits]
    buckets, _ = group_entries(entries, merged)
    return render_release(Release(version, date, entries), buckets, repo_url, hashes)


def render_release(
    release: Release,
    buckets: Mapping[str, list[Entry]],
    repo_url: str | None = None,
    hashes: bool = True,
) -> str:
    lines = [heading_line(release)]
    for heading, items in buckets.items():
        lines += ["", f"### {heading}", ""]
        lines += [render_entry(e, repo_url, hashes) for e in items]
    return "\n".join(lines) + "\n"


def compare_links(releases: list[Release], repo_url: str) -> list[str]:
    """Footer link references (``[1.2.0]: .../compare/v1.1.0...v1.2.0``), newest first."""
    links: list[str] = []
    tagged = [r for r in releases if r.tag]
    for i, r in enumerate(releases):
        label = "Unreleased" if r.version is None else r.version
        older = next((o for o in releases[i + 1 :] if o.tag), None)
        if r.version is None:
            if tagged:
                links.append(f"[{label}]: {repo_url}/compare/{tagged[0].tag}...HEAD")
        elif older is not None:
            links.append(f"[{label}]: {repo_url}/compare/{older.tag}...{r.tag}")
        elif r.tag:
            links.append(f"[{label}]: {repo_url}/releases/tag/{r.tag}")
    return links


def build_changelog(
    releases: list[Release],
    type_map: Mapping[str, str | None] | None = None,
    repo_url: str | None = None,
    hashes: bool = True,
    header: bool = True,
) -> str:
    """A whole CHANGELOG.md: header, every release newest first, compare links."""
    merged = resolve_type_map(dict(type_map) if type_map else None)
    blocks: list[str] = []
    shown: list[Release] = []
    for r in releases:
        buckets, _ = group_entries(r.entries, merged)
        if not buckets and r.version is None:
            continue  # nothing unreleased worth a heading
        blocks.append(render_release(r, buckets, repo_url, hashes))
        shown.append(r)
    text = (HEADER + "\n" if header else "") + "\n".join(blocks)
    if repo_url:
        links = compare_links(shown, repo_url)
        if links:
            text += "\n" + "\n".join(links) + "\n"
    return text
