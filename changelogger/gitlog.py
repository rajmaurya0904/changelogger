"""Read commits, tags and the remote URL out of a git repository."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import GitError, NotAGitRepository

_FIELD = "\x1f"
_RECORD = "\x1e"
_SEMVER = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True)
class RawCommit:
    """A commit as git reports it."""

    sha: str
    date: str  # committer date, YYYY-MM-DD
    message: str  # the full message: subject, blank line, body


@dataclass(frozen=True)
class Tag:
    """A version tag and the commit it points at."""

    name: str
    sha: str
    date: str

    @property
    def version(self) -> str:
        """The tag without a leading ``v``."""
        return self.name[1:] if self.name[:1] in "vV" else self.name


def run_git(repo: Path, *args: str) -> str:
    """Run ``git -C repo args`` and return stdout, translating failures to GitError."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        raise GitError("git was not found on PATH") from None
    except NotADirectoryError:
        raise GitError(f"{repo} is not a directory") from None
    if proc.returncode != 0:
        detail = proc.stderr.strip() or f"git {' '.join(args)} failed"
        if "not a git repository" in detail:
            raise NotAGitRepository("Not a git repository")
        raise GitError(detail.splitlines()[-1] if detail else "git failed")
    return proc.stdout


def ensure_repository(repo: Path) -> Path:
    """Return the top level of the work tree containing ``repo``."""
    if not repo.exists():
        raise GitError(f"directory not found: {repo}")
    return Path(run_git(repo, "rev-parse", "--show-toplevel").strip())


def has_commits(repo: Path) -> bool:
    """False for a freshly initialised repository with no commits yet."""
    try:
        run_git(repo, "rev-parse", "--verify", "--quiet", "HEAD")
    except GitError:
        return False
    return True


def verify_ref(repo: Path, ref: str) -> str:
    """Resolve ``ref`` to a commit sha or raise GitError naming the bad ref."""
    try:
        return run_git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip()
    except NotAGitRepository:
        raise
    except GitError:
        raise GitError(f"unknown tag or revision: {ref}") from None


def read_commits(repo: Path, rev_range: str | None = None) -> list[RawCommit]:
    """Commits in ``rev_range`` (default: everything reachable from HEAD), newest first.

    Merge commits are left out: the commits they merge are listed individually.
    """
    if rev_range is None and not has_commits(repo):
        return []
    fmt = f"%H{_FIELD}%cs{_FIELD}%B{_RECORD}"
    args = ["log", "--no-merges", f"--format={fmt}"]
    args.append(rev_range or "HEAD")
    out = run_git(repo, *args)
    commits: list[RawCommit] = []
    for record in out.split(_RECORD):
        record = record.strip("\n")
        if not record.strip():
            continue
        sha, date, message = record.split(_FIELD, 2)
        commits.append(RawCommit(sha.strip(), date.strip(), message.strip()))
    return commits


def semver_key(name: str) -> tuple[int, int, int, int, tuple[tuple[int, int | str], ...]]:
    """Sort key for version tags. A pre-release sorts before its release."""
    m = _SEMVER.match(name)
    if not m:
        raise ValueError(name)
    pre = m.group("pre")
    ident: tuple[tuple[int, int | str], ...] = ()
    if pre:
        ident = tuple((0, int(p)) if p.isdigit() else (1, p) for p in pre.split("."))
    return (
        int(m.group("major")),
        int(m.group("minor")),
        int(m.group("patch")),
        0 if pre else 1,
        ident,
    )


def list_tags(repo: Path) -> list[Tag]:
    """Semantic-version tags (``v1.2.3`` or ``1.2.3``), oldest version first."""
    out = run_git(
        repo,
        "for-each-ref",
        "refs/tags",
        f"--format=%(refname:short){_FIELD}%(*objectname){_FIELD}%(objectname){_FIELD}"
        f"%(*committerdate:short){_FIELD}%(committerdate:short)",
    )
    tags: list[Tag] = []
    for line in out.splitlines():
        name, peeled, direct, peeled_date, direct_date = line.split(_FIELD)
        if not _SEMVER.match(name):
            continue
        # Annotated tags peel to the commit; lightweight tags are the commit.
        tags.append(Tag(name, peeled or direct, peeled_date or direct_date))
    tags.sort(key=lambda t: semver_key(t.name))
    return tags


def remote_url(repo: Path, remote: str = "origin") -> str | None:
    """The remote as a browsable ``https://host/owner/repo`` URL, if there is one."""
    try:
        raw = run_git(repo, "remote", "get-url", remote).strip()
    except GitError:
        return None
    return normalize_remote(raw)


_URL_REMOTE = re.compile(
    r"^(?:https?|ssh|git)://(?:[^@/]+@)?(?P<host>[\w.-]+)(?::\d+)?/(?P<path>[\w.-]+(?:/[\w.-]+)+?)"
    r"(?:\.git)?/?$"
)
_SCP_REMOTE = re.compile(
    r"^(?:[\w.-]+@)?(?P<host>[\w.-]+):(?P<path>[\w.-]+(?:/[\w.-]+)+?)(?:\.git)?/?$"
)


def normalize_remote(raw: str) -> str | None:
    """Turn ssh/git/https remotes into ``https://host/owner/repo`` (no ``.git`` suffix).

    Returns ``None`` for local paths and anything else that is not a hosted repository.
    """
    raw = raw.strip()
    m = _URL_REMOTE.match(raw) or _SCP_REMOTE.match(raw)
    if not m or "." not in m.group("host"):
        return None
    path = m.group("path").removesuffix("/").removesuffix(".git")
    return f"https://{m.group('host')}/{path}"
