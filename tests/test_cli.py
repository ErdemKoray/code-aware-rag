from pathlib import Path

import pytest
from typer.testing import CliRunner

from coderag.cli import app, format_scan_report
from coderag.scan import ExcludedFile, ExclusionReason, IncludedFile, ScanResult

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("index", "search", "ask", "scan"):
        assert command in result.output


def test_stub_commands_exit_with_error():
    for command in ("index", "search", "ask"):
        result = runner.invoke(app, [command])

        assert result.exit_code == 1
        assert "Not implemented yet." in result.output


# --- scan command ----------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    # Environment variables beat .env, so these tests do not depend on the dev's .env.
    monkeypatch.delenv("FASTAPI_REPO_PATH", raising=False)
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", "500000")


def touch(root: Path, relative: str, content: bytes = b"") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_scan_command_reports_counts_for_a_path(tmp_path):
    touch(tmp_path, "app.py", b"x" * 2500)
    touch(tmp_path, "tests/test_app.py", b"x" * 100)
    touch(tmp_path, "scripts/tool.py")

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "Included: 2 (tests: 1)" in result.output
    assert "Excluded: 0" in result.output
    assert "Pruned directories (1): scripts" in result.output
    assert "Unreadable directories (0): none" in result.output
    assert "2.5 KB  app.py" in result.output
    assert "Scan time:" in result.output


def test_scan_command_lists_every_reason_even_when_zero(tmp_path):
    touch(tmp_path, "app.py")

    result = runner.invoke(app, ["scan", str(tmp_path)])

    for reason in ExclusionReason:
        assert f"  {reason.value}: 0" in result.output


def test_scan_command_defaults_to_configured_repo_path(tmp_path, monkeypatch):
    touch(tmp_path, "only.py")
    monkeypatch.setenv("FASTAPI_REPO_PATH", str(tmp_path))

    result = runner.invoke(app, ["scan"])

    assert result.exit_code == 0
    assert "Included: 1" in result.output
    assert tmp_path.as_posix() in result.output


def test_scan_command_uses_size_limit_from_settings(tmp_path, monkeypatch):
    touch(tmp_path, "small.py", b"x" * 10)
    touch(tmp_path, "big.py", b"x" * 3000)
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", "100")

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert "Max file size: 100 bytes" in result.output
    assert "Included: 1" in result.output
    assert "  too_large: 1" in result.output
    assert "3.0 KB  big.py" in result.output


def test_scan_command_missing_path_fails_with_one_line_error(tmp_path):
    result = runner.invoke(app, ["scan", str(tmp_path / "nope")])

    assert result.exit_code == 2
    assert "Error: scan root does not exist" in result.output
    assert "Traceback" not in result.output


def test_scan_command_file_path_fails(tmp_path):
    touch(tmp_path, "a.py")

    result = runner.invoke(app, ["scan", str(tmp_path / "a.py")])

    assert result.exit_code == 2
    assert "not a directory" in result.output


# --- format_scan_report ----------------------------------------------------


def make_result(**overrides) -> ScanResult:
    fields = {
        "root": Path("repo"),
        "included": (),
        "excluded": (),
        "pruned_dirs": (),
        "unreadable_dirs": (),
    }
    return ScanResult(**{**fields, **overrides})


def test_format_report_for_empty_result():
    report = format_scan_report(make_result(), 500_000, 0.0)

    assert "Included: 0 (tests: 0)" in report
    assert "Pruned directories (0): none" in report
    assert "Largest files:\n  none" in report
    assert "Scan time: 0.00 s" in report


def test_format_report_shows_directories_reasons_and_largest():
    result = make_result(
        included=(IncludedFile("a.py", 1500, False), IncludedFile("tests/t.py", 400, True)),
        excluded=(
            ExcludedFile("big.py", ExclusionReason.TOO_LARGE, 600_000),
            ExcludedFile("link.py", ExclusionReason.SYMLINK),
        ),
        pruned_dirs=(".git", "scripts"),
        unreadable_dirs=("pkg/locked",),
    )

    report = format_scan_report(result, 500_000, 1.234)

    assert "Included: 2 (tests: 1)" in report
    assert "Excluded: 2" in report
    assert "  symlink: 1" in report
    assert "  gitignored: 0" in report
    assert "  too_large: 1" in report
    assert "Pruned directories (2): .git, scripts" in report
    assert "Unreadable directories (1): pkg/locked" in report
    assert report.index("600.0 KB  big.py") < report.index("1.5 KB  a.py")
    assert "Scan time: 1.23 s" in report
