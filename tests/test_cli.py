from typer.testing import CliRunner

from coderag.cli import app

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("index", "search", "ask"):
        assert command in result.output


def test_stub_commands_exit_with_error():
    for command in ("index", "search", "ask"):
        result = runner.invoke(app, [command])

        assert result.exit_code == 1
        assert "Not implemented yet." in result.output
