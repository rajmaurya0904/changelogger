import subprocess
from pathlib import Path

import pytest

from changelogger.errors import GitError, NotAGitRepository
from changelogger.gitlog import (
    ensure_repository,
    has_commits,
    list_tags,
    normalize_remote,
    read_commits,
    remote_url,
    semver_key,
    verify_ref,
)


def test_not_a_git_repository(tmp_path):
    empty = tmp_path / "plain"
    empty.mkdir()
    with pytest.raises(NotAGitRepository, match="Not a git repository"):
        ensure_repository(empty)


def test_missing_directory(tmp_path):
    with pytest.raises(GitError, match="directory not found"):
        ensure_repository(tmp_path / "nope")


def test_ensure_repository_returns_toplevel(repo):
    sub = repo.path / "sub"
    sub.mkdir()
    assert ensure_repository(sub).resolve() == repo.path.resolve()


def test_empty_repository_has_no_commits(repo):
    assert not has_commits(repo.path)
    assert read_commits(repo.path) == []


def test_read_commits_newest_first_with_dates_and_bodies(repo):
    a = repo.commit("feat: one", "2026-01-01T09:00:00+00:00")
    b = repo.commit("fix: two\n\nlonger body\n\nRefs: #3", "2026-01-02T09:00:00+00:00")
    commits = read_commits(repo.path)
    assert [c.sha for c in commits] == [b, a]
    assert commits[0].date == "2026-01-02"
    assert commits[0].message == "fix: two\n\nlonger body\n\nRefs: #3"


def test_merge_commits_are_excluded(repo):
    repo.commit("feat: base")
    default = repo.git("rev-parse", "--abbrev-ref", "HEAD")
    repo.git("checkout", "-q", "-b", "topic")
    repo.commit("feat: on topic")
    repo.git("checkout", "-q", default)
    repo.commit("fix: on main")
    repo.git("merge", "--no-ff", "-q", "-m", "Merge branch topic", "topic")
    messages = [c.message for c in read_commits(repo.path)]
    assert "Merge branch topic" not in messages
    assert set(messages) == {"feat: base", "feat: on topic", "fix: on main"}


def test_unicode_messages_survive(repo):
    repo.commit("feat: support \u00fcber-long names \u2014 and emoji \U0001f600")
    assert read_commits(repo.path)[0].message.startswith("feat: support \u00fcber-long")


def test_tags_sorted_by_version_not_by_name(repo):
    for name in ["v1.10.0", "v1.2.0", "v1.9.1", "not-a-version", "v2.0.0-rc.1", "v2.0.0"]:
        repo.commit(f"fix: for {name}")
        repo.tag(name)
    assert [t.name for t in list_tags(repo.path)] == [
        "v1.2.0",
        "v1.9.1",
        "v1.10.0",
        "v2.0.0-rc.1",
        "v2.0.0",
    ]


def test_tag_details_for_lightweight_and_annotated(released_repo):
    tags = list_tags(released_repo.path)
    assert [(t.name, t.version, t.date) for t in tags] == [
        ("v1.0.0", "1.0.0", "2026-01-11"),
        ("v1.1.0", "1.1.0", "2026-02-03"),
    ]
    first_commit_sha = released_repo.git("rev-parse", "v1.0.0^{commit}")
    assert tags[0].sha == first_commit_sha  # annotated tag is peeled to its commit


def test_range_reads_only_commits_after_a_tag(released_repo):
    commits = read_commits(released_repo.path, "v1.1.0..HEAD")
    assert [c.message for c in commits] == ["docs: tidy", "perf: faster scan"]


def test_verify_ref(released_repo):
    assert verify_ref(released_repo.path, "v1.0.0") == released_repo.git("rev-parse", "v1.0.0^{}")
    with pytest.raises(GitError, match="unknown tag or revision: v9.9.9"):
        verify_ref(released_repo.path, "v9.9.9")


def test_semver_key_orders_prereleases_before_release():
    assert semver_key("v1.0.0-rc.1") < semver_key("v1.0.0")
    assert semver_key("1.0.0-alpha") < semver_key("1.0.0-alpha.1") < semver_key("1.0.0-beta")
    assert semver_key("v1.2.3") == semver_key("1.2.3")
    with pytest.raises(ValueError):
        semver_key("release-3")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("git@github.com:owner/repo.git", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo.git", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo/", "https://github.com/owner/repo"),
        ("https://user:token@github.com/owner/repo", "https://github.com/owner/repo"),
        ("ssh://git@gitlab.com:2222/group/sub/repo.git", "https://gitlab.com/group/sub/repo"),
        ("C:/Users/me/repo", None),
        ("/srv/git/repo.git", None),
        ("../sibling", None),
        ("", None),
    ],
)
def test_normalize_remote(raw, expected):
    assert normalize_remote(raw) == expected


def test_remote_url_reads_origin(repo):
    assert remote_url(repo.path) is None
    repo.git("remote", "add", "origin", "git@github.com:me/thing.git")
    assert remote_url(repo.path) == "https://github.com/me/thing"


def test_git_missing_from_path_is_reported(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(GitError, match="git was not found"):
        ensure_repository(Path(tmp_path))
