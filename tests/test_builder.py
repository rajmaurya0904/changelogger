from changelogger.builder import (
    Entry,
    Release,
    build_changelog,
    build_section,
    entry_from,
    group_entries,
    render_entry,
)
from changelogger.config import resolve_type_map
from changelogger.parser import parse_message


def test_spec_example_dict_gives_added_heading():
    out = build_section([{"type": "feat", "description": "add X"}])
    assert "### Added" in out
    assert "- add X" in out


def test_unreleased_heading_by_default():
    assert build_section([{"type": "fix", "description": "y"}]).startswith("## [Unreleased]\n")


def test_version_and_date_in_heading():
    out = build_section([{"type": "fix", "description": "y"}], "1.2.0", "2026-01-31")
    assert out.startswith("## [1.2.0] - 2026-01-31\n")


def test_sections_follow_keep_a_changelog_order():
    commits = [
        {"type": "security", "description": "s"},
        {"type": "fix", "description": "f"},
        {"type": "remove", "description": "r"},
        {"type": "deprecate", "description": "d"},
        {"type": "perf", "description": "c"},
        {"type": "feat", "description": "a"},
    ]
    out = build_section(commits)
    headings = [line[4:] for line in out.splitlines() if line.startswith("### ")]
    assert headings == ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]


def test_empty_sections_are_not_printed():
    out = build_section([{"type": "feat", "description": "a"}])
    assert "### Fixed" not in out and "### Changed" not in out


def test_hidden_types_are_dropped():
    out = build_section(
        [{"type": "chore", "description": "bump"}, {"type": "docs", "description": "d"}]
    )
    assert out == "## [Unreleased]\n"


def test_order_within_a_section_is_input_order():
    out = build_section(
        [{"type": "feat", "description": "newer"}, {"type": "feat", "description": "older"}]
    )
    assert out.index("newer") < out.index("older")


def test_scope_is_bold_prefix():
    e = Entry("feat", "add flag", scope="cli")
    assert render_entry(e) == "- **cli:** add flag"


def test_breaking_marker_and_note():
    e = Entry("feat", "rename", scope="cli", breaking=True, breaking_notes=("use --output",))
    assert render_entry(e).splitlines() == [
        "- **BREAKING** **cli:** rename",
        "  BREAKING CHANGE: use --output",
    ]


def test_note_identical_to_description_is_not_repeated():
    e = Entry("feat", "same", breaking=True, breaking_notes=("same",))
    assert "\n" not in render_entry(e)


def test_breaking_change_in_hidden_type_surfaces_under_changed():
    out = build_section([{"type": "chore", "description": "drop py3.8", "breaking": True}])
    assert "### Changed" in out
    assert "**BREAKING** drop py3.8" in out


def test_short_hash_without_repo():
    e = Entry("fix", "x", sha="0123456789abcdef")
    assert render_entry(e) == "- x (0123456)"


def test_hash_and_pr_links_with_repo_url():
    e = Entry("fix", "handle empty input (#42)", sha="0123456789abcdef")
    line = render_entry(e, "https://github.com/o/r")
    assert "([#42](https://github.com/o/r/pull/42))" in line
    assert line.endswith("([0123456](https://github.com/o/r/commit/0123456789abcdef))")


def test_hashes_can_be_turned_off():
    e = Entry("fix", "x", sha="0123456789abcdef")
    assert render_entry(e, hashes=False) == "- x"


def test_custom_type_map_changes_heading():
    out = build_section([{"type": "fix", "description": "x"}], type_map={"fix": "Bug Fixes"})
    assert "### Bug Fixes" in out and "### Fixed" not in out


def test_custom_type_map_can_unhide_a_type():
    out = build_section([{"type": "docs", "description": "d"}], type_map={"docs": "Documentation"})
    assert "### Documentation" in out


def test_entry_from_parsed_message_keeps_sha():
    e = entry_from(parse_message("feat(api)!: x\n\nBREAKING CHANGE: y"), sha="abc")
    assert (e.type, e.scope, e.breaking, e.breaking_notes, e.sha) == (
        "feat",
        "api",
        True,
        ("y",),
        "abc",
    )


def test_group_entries_reports_hidden():
    entries = [Entry("feat", "a"), Entry("chore", "b")]
    buckets, hidden = group_entries(entries, resolve_type_map())
    assert list(buckets) == ["Added"] and [h.description for h in hidden] == ["b"]


def test_full_changelog_has_header_and_newest_first():
    releases = [
        Release(None, None, [Entry("feat", "new thing")]),
        Release("1.1.0", "2026-02-01", [Entry("fix", "bug")], tag="v1.1.0"),
        Release("1.0.0", "2026-01-01", [Entry("feat", "first")], tag="v1.0.0"),
    ]
    text = build_changelog(releases)
    assert text.startswith("# Changelog\n")
    assert "keepachangelog.com" in text
    assert text.index("[Unreleased]") < text.index("[1.1.0]") < text.index("[1.0.0]")
    assert "[1.1.0]: " not in text  # no links without a repo url


def test_full_changelog_compare_links():
    releases = [
        Release(None, None, [Entry("feat", "new")]),
        Release("1.1.0", "2026-02-01", [Entry("fix", "bug")], tag="v1.1.0"),
        Release("1.0.0", "2026-01-01", [Entry("feat", "first")], tag="v1.0.0"),
    ]
    text = build_changelog(releases, repo_url="https://github.com/o/r")
    assert "[Unreleased]: https://github.com/o/r/compare/v1.1.0...HEAD" in text
    assert "[1.1.0]: https://github.com/o/r/compare/v1.0.0...v1.1.0" in text
    assert "[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0" in text


def test_empty_unreleased_block_is_skipped_in_full_changelog():
    releases = [
        Release(None, None, [Entry("chore", "x")]),
        Release("1.0.0", "d", [Entry("feat", "a")]),
    ]
    assert "[Unreleased]" not in build_changelog(releases)
