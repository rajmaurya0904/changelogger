"""Shared helpers: throwaway git repositories with controlled commit dates."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


class Repo:
    """A temporary git repository driven through the real git binary."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._counter = 0
        self.git("init", "-q")

    def git(self, *args: str, date: str | None = None, stdin: str | None = None) -> str:
        env = dict(os.environ)
        env.update(
            GIT_AUTHOR_NAME="Test User",
            GIT_AUTHOR_EMAIL="test@example.com",
            GIT_COMMITTER_NAME="Test User",
            GIT_COMMITTER_EMAIL="test@example.com",
        )
        if date:
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = date
        proc = subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgsign=false",
                "-C",
                str(self.path),
                *args,
            ],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=True,
        )
        return proc.stdout.strip()

    def commit(self, message: str, date: str | None = None) -> str:
        """Create an empty commit and return its sha."""
        self._counter += 1
        if date is None:
            date = f"2026-03-{min(self._counter, 28):02d}T12:00:00+00:00"
        self.git("commit", "-q", "--allow-empty", "-F", "-", date=date, stdin=message)
        return self.git("rev-parse", "HEAD")

    def tag(self, name: str, annotated: bool = False, date: str | None = None) -> None:
        if annotated:
            self.git("tag", "-a", name, "-m", f"release {name}", date=date)
        else:
            self.git("tag", name)


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    root = tmp_path / "work"
    root.mkdir()
    return Repo(root)


@pytest.fixture
def released_repo(repo: Repo) -> Repo:
    """Two tagged releases plus unreleased work, with a mix of message styles."""
    repo.commit("feat: first feature", "2026-01-10T10:00:00+00:00")
    repo.commit("chore: scaffold", "2026-01-11T10:00:00+00:00")
    repo.tag("v1.0.0", annotated=True, date="2026-01-12T10:00:00+00:00")
    repo.commit("fix(parser): handle empty input (#7)", "2026-02-01T10:00:00+00:00")
    repo.commit("Update README", "2026-02-02T10:00:00+00:00")
    repo.commit(
        "feat(cli)!: rename --out\n\nBREAKING CHANGE: use --output", "2026-02-03T10:00:00+00:00"
    )
    repo.tag("v1.1.0", date="2026-02-04T10:00:00+00:00")
    repo.commit("perf: faster scan", "2026-03-01T10:00:00+00:00")
    repo.commit("docs: tidy", "2026-03-02T10:00:00+00:00")
    return repo
