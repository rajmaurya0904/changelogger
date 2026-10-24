"""collect() turns real git history into releases."""

from __future__ import annotations

import pytest

from changelogger.errors import GitError
from changelogger.generate import collect


def versions(result) -> list[str | None]:
    return [r.version for r in result.releases]


def test_releases_are_newest_first_with_unreleased_on_top(released_repo) -> None:
    result = collect(released_repo.path)
    assert versions(result) == [None, "1.1.0", "1.0.0"]


def test_commits_land_in_the_release_they_were_tagged_in(released_repo) -> None:
    result = collect(released_repo.path)
    by_version = {r.version: [e.description for e in r.entries] for r in result.releases}
    assert by_version["1.0.0"] == ["scaffold", "first feature"]
    assert by_version["1.1.0"] == ["rename --out", "handle empty input (#7)"]
    assert by_version[None] == ["tidy", "faster scan"]


def test_non_conventional_commits_are_collected_separately(released_repo) -> None:
    result = collect(released_repo.path)
    assert [c.message for c in result.skipped] == ["Update README"]
    assert result.entry_count == 6


def test_release_carries_its_tag_name(released_repo) -> None:
    tags = {r.version: r.tag for r in collect(released_repo.path).releases}
    assert tags == {None: None, "1.1.0": "v1.1.0", "1.0.0": "v1.0.0"}


def test_breaking_footer_is_kept(released_repo) -> None:
    release = next(r for r in collect(released_repo.path).releases if r.version == "1.1.0")
    breaking = [e for e in release.entries if e.breaking]
    assert len(breaking) == 1
    assert breaking[0].scope == "cli"
    assert breaking[0].breaking_notes == ("use --output",)


def test_no_tags_means_everything_is_unreleased(repo) -> None:
    repo.commit("feat: one")
    repo.commit("fix: two")
    result = collect(repo.path)
    assert versions(result) == [None]
    assert [e.description for e in result.releases[0].entries] == ["two", "one"]


def test_empty_repository(repo) -> None:
    result = collect(repo.path)
    assert result.entry_count == 0
    assert result.skipped == []


def test_non_version_tags_are_ignored(repo) -> None:
    repo.commit("feat: one")
    repo.tag("nightly")
    repo.tag("release-candidate")
    assert versions(collect(repo.path)) == [None]


def test_prerelease_tag_sorts_before_its_release(repo) -> None:
    repo.commit("feat: a")
    repo.tag("v1.0.0-rc.1")
    repo.commit("fix: b")
    repo.tag("v1.0.0")
    assert versions(collect(repo.path)) == [None, "1.0.0", "1.0.0-rc.1"]


def test_tag_on_head_leaves_no_unreleased_commits(repo) -> None:
    repo.commit("feat: a")
    repo.tag("v0.1.0")
    result = collect(repo.path)
    assert result.releases[0].version is None
    assert result.releases[0].entries == []
    assert result.releases[1].version == "0.1.0"


def test_merge_commits_are_not_listed(repo) -> None:
    repo.commit("feat: base")
    repo.git("checkout", "-q", "-b", "topic")
    repo.commit("fix: on topic")
    repo.git("checkout", "-q", "-")
    repo.commit("feat: on main")
    repo.git("merge", "--no-ff", "-q", "-m", "Merge branch topic", "topic")
    result = collect(repo.path)
    names = sorted(e.description for e in result.releases[0].entries)
    assert names == ["base", "on main", "on topic"]
    assert result.skipped == []


def test_since_and_until_select_a_window(released_repo) -> None:
    result = collect(released_repo.path, since="v1.0.0", until="v1.1.0")
    assert versions(result) == ["1.1.0"]


def test_since_accepts_tag_without_prefix(released_repo) -> None:
    assert versions(collect(released_repo.path, since="1.0.0")) == [None, "1.1.0"]


def test_arbitrary_rev_is_one_unreleased_block(released_repo) -> None:
    result = collect(released_repo.path, since="HEAD~3")
    assert versions(result) == [None]
    got = [e.description for e in result.releases[0].entries]
    assert got == ["tidy", "faster scan", "rename --out"]


def test_unknown_ref_raises(released_repo) -> None:
    with pytest.raises(GitError, match="unknown tag or revision"):
        collect(released_repo.path, until="nonsense")
