import pytest

from changelogger.parser import ParsedMessage, parse_commit, parse_message


def test_basic_header():
    m = parse_message("feat(core): add parser")
    assert m == ParsedMessage("feat", "add parser", "core", False, (), "")


def test_no_scope():
    m = parse_message("fix: correct typo")
    assert (m.type, m.scope, m.description) == ("fix", None, "correct typo")


def test_type_is_lowercased():
    assert parse_message("FEAT: Shout").type == "feat"


def test_bang_marks_breaking_with_and_without_scope():
    assert parse_message("feat!: overhaul API").breaking
    m = parse_message("refactor(db)!: drop sqlite")
    assert m.breaking and m.scope == "db"


def test_breaking_change_footer_with_note():
    msg = "feat: new config\n\nBody text here.\n\nBREAKING CHANGE: the old file is ignored"
    m = parse_message(msg)
    assert m.breaking
    assert m.breaking_notes == ("the old file is ignored",)
    assert m.body.startswith("Body text here.")


def test_breaking_hyphen_footer_and_continuation_lines():
    msg = "fix: x\n\nBREAKING-CHANGE: first line\ncontinues here\n\nRefs: #4"
    assert parse_message(msg).breaking_notes == ("first line continues here",)


def test_footer_continuation_stops_at_next_trailer():
    msg = "fix: x\n\nBREAKING CHANGE: gone\nReviewed-by: Someone"
    assert parse_message(msg).breaking_notes == ("gone",)


def test_multiple_breaking_footers():
    msg = "feat: x\n\nBREAKING CHANGE: a\n\nBREAKING CHANGE: b"
    assert parse_message(msg).breaking_notes == ("a", "b")


def test_mentioning_the_phrase_in_prose_is_not_breaking():
    msg = "docs: explain things\n\nThe words BREAKING CHANGE: appear mid-line here."
    assert not parse_message(msg).breaking


def test_windows_line_endings():
    m = parse_message("feat: a\r\n\r\nBREAKING CHANGE: b\r\n")
    assert m.breaking_notes == ("b",)


@pytest.mark.parametrize(
    "message",
    [
        "",
        "   ",
        "Update README",
        "Merge branch 'main' into feature",
        "feat:no space",
        "feat(): empty scope",
        "feat: ",
        ": missing type",
        "feat add thing",
        "123: numbers are not a type",
        "feat(a)(b): double scope",
    ],
)
def test_non_conventional_messages_are_rejected(message):
    assert parse_message(message) is None


def test_git_revert_message_is_read_as_revert():
    m = parse_message('Revert "feat: add flux capacitor"\n\nThis reverts commit abc123.')
    assert (m.type, m.description) == ("revert", "feat: add flux capacitor")


def test_description_may_contain_colons_and_parentheses():
    m = parse_message("fix(api): handle a: b (and c)")
    assert m.description == "handle a: b (and c)"


def test_legacy_parse_commit_still_lenient():
    assert parse_commit("feat") == {
        "type": "feat",
        "scope": None,
        "description": "",
        "breaking": False,
    }


def test_legacy_parse_commit_footer_only_counts_at_line_start():
    assert parse_commit("feat: a\n\nBREAKING CHANGE: b")["breaking"] is True
    assert parse_commit("feat: a\n\nmentions BREAKING CHANGE: b")["breaking"] is False


def test_legacy_parse_commit_description_is_first_line_only():
    assert parse_commit("fix: one\n\nlong body")["description"] == "one"
