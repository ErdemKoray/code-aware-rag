from pathlib import Path

import pytest
from typer.testing import CliRunner

from coderag.cli import app, format_parse_debug, format_scan_report
from coderag.parsing.python import parse
from coderag.scan import ExcludedFile, ExclusionReason, IncludedFile, ScanResult

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("index", "search", "ask", "scan", "parse-debug"):
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


# --- parse-debug command ---------------------------------------------------

SAMPLE = (
    b"# header comment\n"
    b"import os\n"
    b"\n"
    b"async def fetch():\n"
    b"    return 1\n"
    b"\n"
    b"@decorator\n"
    b"@other\n"
    b"class Outer:\n"
    b"    class Inner:\n"
    b"        pass\n"
)


def node_lines(output: str) -> list[list[str]]:
    """Split every line after the has_error line into whitespace separated tokens."""
    return [line.split() for line in output.splitlines()[1:]]


def test_parse_debug_prints_has_error_first_then_top_level_nodes(tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_bytes(SAMPLE)

    result = runner.invoke(app, ["parse-debug", str(source_file)])

    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "has_error: False"
    assert node_lines(result.output) == [
        ["comment", "L1-1"],
        ["import_statement", "L2-2"],
        ["function_definition", "L4-5", "name=fetch"],
        ["decorated_definition", "L7-11", "name=Outer"],
    ]


def test_parse_debug_uses_one_based_inclusive_ranges_with_ascii_dash(tmp_path):
    source_file = tmp_path / "one.py"
    source_file.write_bytes(b"def f():\n    pass\n")

    result = runner.invoke(app, ["parse-debug", str(source_file)])

    assert "L1-2" in result.output
    assert result.output.isascii()


def test_parse_debug_reports_syntax_errors_with_exit_code_zero(tmp_path):
    source_file = tmp_path / "broken.py"
    source_file.write_bytes(b"def f(:\n    pass\n\nclass B:\n    x = 1\n")

    result = runner.invoke(app, ["parse-debug", str(source_file)])

    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "has_error: True"
    assert node_lines(result.output) == [
        ["function_definition", "L1-2", "name=f"],
        ["class_definition", "L4-5", "name=B"],
    ]


def test_parse_debug_empty_file(tmp_path):
    source_file = tmp_path / "empty.py"
    source_file.write_bytes(b"")

    result = runner.invoke(app, ["parse-debug", str(source_file)])

    assert result.exit_code == 0
    assert result.output.splitlines() == ["has_error: False", "(no top-level nodes)"]


def test_parse_debug_missing_file_exits_with_code_two(tmp_path):
    result = runner.invoke(app, ["parse-debug", str(tmp_path / "nope.py")])

    assert result.exit_code == 2
    assert "Error: cannot read" in result.output
    assert "Traceback" not in result.output


def test_parse_debug_directory_exits_with_code_two(tmp_path):
    result = runner.invoke(app, ["parse-debug", str(tmp_path)])

    assert result.exit_code == 2
    assert "Error: cannot read" in result.output


def test_parse_debug_requires_a_path():
    result = runner.invoke(app, ["parse-debug"])

    assert result.exit_code == 2


def test_format_parse_debug_names_only_functions_and_classes():
    report = format_parse_debug(parse(b"x = 1\ndef f(): ...\nclass C: ...\n"))

    assert node_lines(report) == [
        ["expression_statement", "L1-1"],
        ["function_definition", "L2-2", "name=f"],
        ["class_definition", "L3-3", "name=C"],
    ]


def test_format_parse_debug_aligns_columns_to_the_longest_type():
    report = format_parse_debug(parse(b"x = 1\ndef f(): ...\n"))

    first, second = report.splitlines()[1:]
    assert first.index("L1-1") == second.index("L2-2")


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
