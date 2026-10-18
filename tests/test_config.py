import json

import pytest

from changelogger.config import (
    DEFAULT_TYPE_MAP,
    parse_type_map,
    resolve_type_map,
    section_order,
)
from changelogger.errors import ConfigError


def test_defaults_cover_the_usual_types():
    assert DEFAULT_TYPE_MAP["feat"] == "Added"
    assert DEFAULT_TYPE_MAP["fix"] == "Fixed"
    assert DEFAULT_TYPE_MAP["chore"] is None


def test_inline_json():
    assert parse_type_map('{"fix": "Bug Fixes"}') == {"fix": "Bug Fixes"}


def test_keys_are_lowercased_and_null_hides():
    assert parse_type_map('{"FEAT": "Features", "perf": null, "docs": ""}') == {
        "feat": "Features",
        "perf": None,
        "docs": None,
    }


def test_json_file(tmp_path):
    p = tmp_path / "map.json"
    p.write_text(json.dumps({"docs": "Documentation"}))
    assert parse_type_map(str(p)) == {"docs": "Documentation"}


def test_missing_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="neither a JSON object nor an existing file"):
        parse_type_map(str(tmp_path / "nope.json"))


@pytest.mark.parametrize("bad", ['{"fix": ', '{"fix": 3}', '{"fix": ["a"]}'])
def test_bad_json_rejected(bad):
    with pytest.raises(ConfigError):
        parse_type_map(bad)


def test_non_object_json_file_rejected(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2]")
    with pytest.raises(ConfigError, match="JSON object"):
        parse_type_map(str(p))


def test_override_merges_over_defaults():
    merged = resolve_type_map({"fix": "Bug Fixes", "docs": "Documentation"})
    assert merged["fix"] == "Bug Fixes"
    assert merged["docs"] == "Documentation"
    assert merged["feat"] == "Added"


def test_override_can_hide_a_default():
    assert resolve_type_map({"perf": None})["perf"] is None


def test_section_order_puts_standard_headings_first_then_custom():
    order = section_order(resolve_type_map({"fix": "Bug Fixes", "docs": "Documentation"}))
    assert order[:6] == ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    assert order.index("Bug Fixes") < order.index("Documentation")
