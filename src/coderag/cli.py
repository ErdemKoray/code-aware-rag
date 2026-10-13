import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Code-aware RAG over Python repositories.",
)


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
