import time
from pathlib import Path
from typing import Annotated

import typer

from coderag.config import Settings
from coderag.scan import ScanResult, scan

app = typer.Typer(
    no_args_is_help=True,
    help="Code-aware RAG over Python repositories.",
)


def _format_dirs(label: str, dirs: tuple[str, ...]) -> str:
    return f"{label} ({len(dirs)}): " + (", ".join(dirs) if dirs else "none")


def format_scan_report(result: ScanResult, max_file_size_bytes: int, elapsed_seconds: float) -> str:
    """Render a scan result as plain text. KB here means 1000 bytes, like the size limit."""
    lines = [
        f"Scan root: {result.root.as_posix()}",
        f"Max file size: {max_file_size_bytes} bytes",
        f"Included: {len(result.included)} (tests: {result.test_count})",
        f"Excluded: {len(result.excluded)}",
    ]
    lines += [f"  {reason.value}: {count}" for reason, count in result.exclusion_counts.items()]
    lines.append(_format_dirs("Pruned directories", result.pruned_dirs))
    lines.append(_format_dirs("Unreadable directories", result.unreadable_dirs))
    lines.append("Largest files:")
    largest = result.largest(5)
    if largest:
        lines += [f"  {size / 1000:>8.1f} KB  {path}" for path, size in largest]
    else:
        lines.append("  none")
    lines.append(f"Scan time: {elapsed_seconds:.2f} s")
    return "\n".join(lines)


@app.command("scan")
def scan_command(
    path: Annotated[
        Path | None,
        typer.Argument(help="Directory to scan. Defaults to the configured FastAPI repo."),
    ] = None,
) -> None:
    """List the .py files that would be indexed, and why the others are excluded."""
    settings = Settings()
    root = path if path is not None else settings.fastapi_repo_path
    started = time.perf_counter()
    try:
        result = scan(root, settings.max_file_size_bytes)
    except OSError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    elapsed = time.perf_counter() - started
    typer.echo(format_scan_report(result, settings.max_file_size_bytes, elapsed))


@app.command()
def index() -> None:
    """Index a repository."""
    typer.echo("Not implemented yet.")
    raise typer.Exit(code=1)


@app.command()
def search() -> None:
    """Search the index without generating an answer."""
    typer.echo("Not implemented yet.")
    raise typer.Exit(code=1)


@app.command()
def ask() -> None:
    """Ask a question and get a cited answer."""
    typer.echo("Not implemented yet.")
    raise typer.Exit(code=1)
