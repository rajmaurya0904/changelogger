"""Walk git history and assemble :class:`~changelogger.builder.Release` blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .builder import Entry, Release
from .errors import GitError
from .gitlog import RawCommit, Tag, list_tags, read_commits, verify_ref
from .parser import parse_message


@dataclass
class Collected:
    """Releases newest first, plus the commits that were not conventional."""

    releases: list[Release] = field(default_factory=list)
    skipped: list[RawCommit] = field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return sum(len(r.entries) for r in self.releases)


def _entries(commits: list[RawCommit], skipped: list[RawCommit]) -> list[Entry]:
    out: list[Entry] = []
    for c in commits:
        parsed = parse_message(c.message)
        if parsed is None:
            skipped.append(c)
            continue
        out.append(
            Entry(
                parsed.type,
                parsed.description,
                parsed.scope,
                parsed.breaking,
                parsed.breaking_notes,
                c.sha,
            )
        )
    return out


def _tag_named(tags: list[Tag], name: str | None) -> Tag | None:
    if name is None:
        return None
    for t in tags:
        if t.name == name or t.version == name.lstrip("vV"):
            return t
    return None


def collect(repo: Path, since: str | None = None, until: str | None = None) -> Collected:
    """Read history into releases.

    Each semantic-version tag becomes a release holding the commits between it and the
    previous tag; commits after the newest tag form ``Unreleased``. ``since`` drops
    releases at or before that tag, ``until`` drops releases after it (and Unreleased).
    If either names something that is not a version tag (a branch, a sha), the range
    ``since..until`` is read as a single block instead.
    """
    tags = list_tags(repo)
    result = Collected()
    since_tag, until_tag = _tag_named(tags, since), _tag_named(tags, until)
    custom = (since is not None and since_tag is None) or (until is not None and until_tag is None)

    if custom:
        for ref in (since, until):
            if ref is not None:
                verify_ref(repo, ref)
        rng = f"{since}..{until or 'HEAD'}" if since else (until or "HEAD")
        commits = read_commits(repo, rng)
        version = until_tag.version if until_tag else None
        date = until_tag.date if until_tag else None
        result.releases.append(Release(version, date, _entries(commits, result.skipped)))
        return result

    if since_tag and until_tag and tags.index(since_tag) >= tags.index(until_tag):
        raise GitError(f"--since {since} is not older than --until {until}")

    prev_sha: str | None = None
    built: list[Release] = []
    for tag in tags:
        rng = f"{prev_sha}..{tag.sha}" if prev_sha else tag.sha
        entries = _entries(read_commits(repo, rng), result.skipped)
        built.append(Release(tag.version, tag.date, entries, tag.name))
        prev_sha = tag.sha
    if until_tag is None:
        rng = f"{prev_sha}..HEAD" if prev_sha else None
        built.append(Release(None, None, _entries(read_commits(repo, rng), result.skipped)))

    lo = tags.index(since_tag) + 1 if since_tag else 0
    hi = tags.index(until_tag) + 1 if until_tag else len(built)
    result.releases = list(reversed(built[lo:hi]))
    return result
