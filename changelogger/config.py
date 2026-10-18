"""Mapping from commit types to Keep a Changelog section headings."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ConfigError

# The six headings defined by Keep a Changelog, in the order they are printed.
STANDARD_SECTIONS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

# A type mapped to None (or an empty string) is left out of the changelog.
DEFAULT_TYPE_MAP: dict[str, str | None] = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "change": "Changed",
    "revert": "Changed",
    "deprecate": "Deprecated",
    "remove": "Removed",
    "security": "Security",
    "docs": None,
    "style": None,
    "test": None,
    "build": None,
    "ci": None,
    "chore": None,
}

# Breaking changes are always listed, even for types that are normally hidden.
BREAKING_FALLBACK_SECTION = "Changed"


def parse_type_map(value: str) -> dict[str, str | None]:
    """Read a ``--type-map`` argument: inline JSON, or the path of a JSON file.

    The result maps a commit type to a heading, or to ``null`` to hide that type.
    """
    text = value.strip()
    if not text.startswith("{"):
        path = Path(text)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise ConfigError(
                f"--type-map is neither a JSON object nor an existing file: {value!r}"
            ) from None
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigError(f"cannot read type map {path}: {exc}") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"type map is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError('type map must be a JSON object such as {"fix": "Bug Fixes"}')
    out: dict[str, str | None] = {}
    for key, heading in data.items():
        if heading is not None and not isinstance(heading, str):
            raise ConfigError(f"type map entry {key!r} must be a heading string or null")
        out[str(key).strip().lower()] = heading.strip() if heading else None
    return out


def resolve_type_map(override: dict[str, str | None] | None = None) -> dict[str, str | None]:
    """Defaults with ``override`` applied on top."""
    merged = dict(DEFAULT_TYPE_MAP)
    if override:
        merged.update({k.lower(): v for k, v in override.items()})
    return merged


def section_order(type_map: dict[str, str | None]) -> list[str]:
    """Headings in print order: the standard six, then custom ones as first defined."""
    order = list(STANDARD_SECTIONS)
    for heading in type_map.values():
        if heading and heading not in order:
            order.append(heading)
    if BREAKING_FALLBACK_SECTION not in order:
        order.append(BREAKING_FALLBACK_SECTION)
    return order
