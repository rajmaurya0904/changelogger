"""End-to-end tests of the command line against throwaway git repositories."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from changelogger import __version__
from changelogger.cli import main


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "changelogger", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage: changelogger" in out
    assert "--type-map" in out


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_module_entry_point_prints_changelog(released_repo) -> None:
    proc = run_cli(str(released_repo.path), "--no-hashes", "--no-links")
    assert proc.returncode == 0
    assert proc.stdout.startswith("# Changelog")
    assert "## [Unreleased]" in proc.stdout
    assert "## [1.1.0] - 2026-02-03" in proc.stdout
    assert "## [1.0.0] - 2026-01-11" in proc.stdout


def test_sections_and_entries(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--no-hashes"]) == 0
    out = capsys.readouterr().out
    assert "- first feature" in out
    assert "- **parser:** handle empty input (#7)" in out
    assert "- **BREAKING** **cli:** rename --out" in out
    assert "BREAKING CHANGE: use --output" in out
    assert "scaffold" not in out  # chore is hidden by default
    assert "tidy" not in out  # docs too


def test_nonconventional_commits_are_skipped_with_warning(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "-v"]) == 0
    cap = capsys.readouterr()
    assert "Update README" not in cap.out
    assert "skipped 1 non-conventional commit" in cap.err
    assert "Update README" in cap.err


def test_strict_fails_on_nonconventional(released_repo) -> None:
    assert main([str(released_repo.path), "--strict"]) == 2


def test_not_a_git_repository(tmp_path: Path, capsys) -> None:
    empty = tmp_path / "plain"
    empty.mkdir()
    assert main([str(empty)]) == 1
    assert "Not a git repository" in capsys.readouterr().err


def test_not_a_git_repository_via_subprocess(tmp_path: Path) -> None:
    proc = run_cli(str(tmp_path))
    assert proc.returncode == 1
    assert "Not a git repository" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_missing_directory(tmp_path: Path, capsys) -> None:
    assert main([str(tmp_path / "nope")]) == 1
    assert "not found" in capsys.readouterr().err


def test_repository_without_commits(repo, capsys) -> None:
    assert main([str(repo.path)]) == 0
    assert "No conventional commits found" in capsys.readouterr().out


def test_only_nonconventional_commits(repo, capsys) -> None:
    repo.commit("Initial commit")
    assert main([str(repo.path)]) == 0
    assert "No conventional commits found" in capsys.readouterr().out


def test_type_map_inline_json_renames_heading(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--type-map", '{"fix": "Bug Fixes"}']) == 0
    out = capsys.readouterr().out
    assert "### Bug Fixes" in out
    assert "### Fixed" not in out


def test_type_map_can_show_hidden_types(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--type-map", '{"docs": "Documentation"}']) == 0
    out = capsys.readouterr().out
    assert "### Documentation" in out
    assert "tidy" in out


def test_type_map_from_file(released_repo, tmp_path: Path, capsys) -> None:
    f = tmp_path / "map.json"
    f.write_text(json.dumps({"feat": "New"}), encoding="utf-8")
    assert main([str(released_repo.path), "--type-map", str(f)]) == 0
    assert "### New" in capsys.readouterr().out


def test_bad_type_map(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--type-map", "{nope"]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_since_tag_limits_output(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "v1.0.0", "--no-hashes"]) == 0
    out = capsys.readouterr().out
    assert "## [1.1.0]" in out
    assert "## [Unreleased]" in out
    assert "## [1.0.0]" not in out
    assert "first feature" not in out


def test_until_tag_limits_output(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--until", "v1.0.0"]) == 0
    out = capsys.readouterr().out
    assert "## [1.0.0]" in out
    assert "## [1.1.0]" not in out
    assert "## [Unreleased]" not in out


def test_since_and_until_window(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "v1.0.0", "--until", "v1.1.0"]) == 0
    out = capsys.readouterr().out
    assert "## [1.1.0]" in out
    assert "## [1.0.0]" not in out and "## [Unreleased]" not in out


def test_since_tag_without_v_prefix(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "1.0.0"]) == 0
    assert "## [1.0.0]" not in capsys.readouterr().out


def test_since_unknown_ref(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "v9.9.9"]) == 1
    assert "unknown tag or revision: v9.9.9" in capsys.readouterr().err


def test_since_after_until_is_rejected(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "v1.1.0", "--until", "v1.0.0"]) == 1
    assert "not older" in capsys.readouterr().err


def test_since_arbitrary_revision_makes_single_block(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "HEAD~2", "--no-hashes"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n## [") == 1
    assert "faster scan" in out
    assert "tidy" not in out  # docs is hidden
    assert "rename --out" not in out  # older than HEAD~2


def test_range_of_only_hidden_types(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--since", "HEAD~1"]) == 0
    assert "No user-facing changes" in capsys.readouterr().out


def test_unreleased_only(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--unreleased", "--no-hashes"]) == 0
    out = capsys.readouterr().out
    assert "faster scan" in out
    assert "## [1.1.0]" not in out


def test_release_names_unreleased_block(released_repo, capsys) -> None:
    code = main([str(released_repo.path), "--release", "v1.2.0", "--date", "2026-04-01"])
    assert code == 0
    out = capsys.readouterr().out
    assert "## [1.2.0] - 2026-04-01" in out
    assert "Unreleased" not in out


def test_release_without_unreleased_commits_fails(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--until", "v1.0.0", "--release", "2.0.0"]) == 1
    assert "unreleased commits" in capsys.readouterr().err


def test_date_requires_release(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--date", "2026-01-01"]) == 1
    assert "--release" in capsys.readouterr().err


def test_bad_date(released_repo, capsys) -> None:
    assert main([str(released_repo.path), "--release", "1.2.0", "--date", "yesterday"]) == 1
    assert "--date must look like" in capsys.readouterr().err


def test_output_file(released_repo, tmp_path: Path, capsys) -> None:
    target = tmp_path / "CHANGELOG.md"
    assert main([str(released_repo.path), "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8").startswith("# Changelog")
    assert capsys.readouterr().out == ""


def test_output_to_unwritable_path(released_repo, tmp_path: Path, capsys) -> None:
    assert main([str(released_repo.path), "-o", str(tmp_path / "missing" / "x.md")]) == 1
    assert "cannot write" in capsys.readouterr().err


def test_links_use_the_origin_remote(released_repo, capsys) -> None:
    released_repo.git("remote", "add", "origin", "git@github.com:acme/widget.git")
    assert main([str(released_repo.path)]) == 0
    out = capsys.readouterr().out
    assert "https://github.com/acme/widget/pull/7" in out
    assert "[1.1.0]: https://github.com/acme/widget/compare/v1.0.0...v1.1.0" in out
    assert "[Unreleased]: https://github.com/acme/widget/compare/v1.1.0...HEAD" in out


def test_no_links_flag(released_repo, capsys) -> None:
    released_repo.git("remote", "add", "origin", "https://github.com/acme/widget.git")
    assert main([str(released_repo.path), "--no-links"]) == 0
    assert "github.com" not in capsys.readouterr().out
