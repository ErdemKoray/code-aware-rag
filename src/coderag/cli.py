import time
from pathlib import Path
from typing import Annotated

import typer
from tree_sitter import Node

from coderag.chunking.chunker import chunk_source
from coderag.chunking.model import Chunk
from coderag.config import Settings
from coderag.parsing.python import ParseResult, line_range, parse
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


def _definition_name(node: Node, source: bytes) -> str | None:
    """Name of a function or class; a decorated definition reports the name it wraps."""
    if node.type == "decorated_definition":
        definition = node.child_by_field_name("definition")
        if definition is None:
            return None
        node = definition
    if node.type not in ("function_definition", "class_definition"):
        return None
    name = node.child_by_field_name("name")
    if name is None:
        return None
    return source[name.start_byte : name.end_byte].decode("utf-8", errors="replace")


def format_parse_debug(result: ParseResult) -> str:
    """Render the top-level named nodes of a parse as one line each, after a has_error line."""
    lines = [f"has_error: {result.has_error}"]
    nodes = result.tree.root_node.named_children
    if not nodes:
        lines.append("(no top-level nodes)")
    width = max((len(node.type) for node in nodes), default=0)
    for node in nodes:
        first, last = line_range(node)
        line = f"{node.type:<{width}}  L{first}-{last}"
        name = _definition_name(node, result.source)
        if name is not None:
            line += f"  name={name}"
        lines.append(line)
    return "\n".join(lines)


def _read_source(path: Path) -> bytes:
    """The bytes of a file, or a one-line error and exit code 2."""
    try:
        return path.read_bytes()
    except OSError as error:
        typer.echo(f"Error: cannot read {path}: {error.strerror or error}", err=True)
        raise typer.Exit(code=2) from error


@app.command("parse-debug")
def parse_debug(path: Annotated[Path, typer.Argument(help="Python file to parse.")]) -> None:
    """Print the top-level syntax nodes of a Python file with their line ranges."""
    source = _read_source(path)
    # A file with syntax errors is still reported (exit code 0): this tool describes, it
    # does not judge.
    typer.echo(format_parse_debug(parse(source)))


def format_chunk_debug(chunks: tuple[Chunk, ...], has_error: bool, max_chunk_bytes: int) -> str:
    """Render one line per chunk: kind, lines, size, name, part and unchunked names."""
    lines = [
        f"has_error: {has_error}",
        f"chunks: {len(chunks)} (max size: {max_chunk_bytes} bytes)",
    ]
    kind_width = max((len(chunk.kind) for chunk in chunks), default=0)
    ranges = [f"L{chunk.start_line}-{chunk.end_line}" for chunk in chunks]
    range_width = max((len(text) for text in ranges), default=0)
    size_width = max((len(str(chunk.size_bytes)) for chunk in chunks), default=0)
    for chunk, line_text in zip(chunks, ranges, strict=True):
        line = (
            f"{chunk.kind:<{kind_width}}  {line_text:<{range_width}}  "
            f"{chunk.size_bytes:>{size_width}} B"
        )
        if chunk.qualname is not None:
            line += f"  {chunk.qualname}"
        if chunk.part_count > 1:
            line += f"  [{chunk.part}/{chunk.part_count}]"
        if chunk.defined_names:
            line += f"  defines: {', '.join(chunk.defined_names)}"
        lines.append(line)
    return "\n".join(lines)


@app.command("chunk-debug")
def chunk_debug(path: Annotated[Path, typer.Argument(help="Python file to chunk.")]) -> None:
    """Print the chunks of a Python file with their line ranges and sizes."""
    source = _read_source(path)
    max_chunk_bytes = Settings().max_chunk_bytes
    chunks = chunk_source(source, path.as_posix(), max_chunk_bytes)
    typer.echo(format_chunk_debug(chunks, parse(source).has_error, max_chunk_bytes))


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
