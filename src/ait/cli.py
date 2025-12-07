"""CLI for ait - Archive of Interconnected Terms."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ait import __version__

app = typer.Typer(
    name="ait",
    help="Archive of Interconnected Terms - A local-first MCP server for ontology work",
    no_args_is_help=True,
)
console = Console()


@app.command()
def serve(
    data_dir: Path = typer.Option(
        Path.home() / ".ait",
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
    bioportal_key: str | None = typer.Option(
        None,
        "--bioportal-key",
        "-k",
        envvar="BIOPORTAL_API_KEY",
        help="BioPortal API key",
    ),
) -> None:
    """Start the MCP server (stdio transport for Claude Code integration)."""
    from ait.server import ServerConfig, configure, run_stdio

    config = ServerConfig(
        data_dir=data_dir,
        bioportal_api_key=bioportal_key,
    )
    configure(config)

    console.print(f"[bold green]ait[/] v{__version__}", style="dim")
    console.print(f"Data directory: {data_dir}", style="dim")
    console.print("Starting MCP server on stdio...", style="dim")

    asyncio.run(run_stdio())


@app.command()
def status(
    data_dir: Path = typer.Option(
        Path.home() / ".ait",
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
) -> None:
    """Show status of local store."""
    from ait.store import Store

    store_path = data_dir / "store"
    if not store_path.exists():
        console.print("[yellow]No local store found.[/]")
        console.print(f"Run [bold]ait serve[/] to create one at {store_path}")
        return

    store = Store(store_path)
    graphs = list(store.graphs())

    console.print(f"[bold]Store:[/] {store_path}")
    console.print(f"[bold]Total triples:[/] {len(store)}")
    console.print(f"[bold]Named graphs:[/] {len(graphs)}")

    if graphs:
        table = Table(title="Cached Ontologies")
        table.add_column("Graph URI")
        for g in graphs:
            table.add_row(g)
        console.print(table)


@app.command()
def clear(
    data_dir: Path = typer.Option(
        Path.home() / ".ait",
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
    graph: str | None = typer.Option(
        None,
        "--graph",
        "-g",
        help="Specific graph to clear (default: all)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
) -> None:
    """Clear cached data from local store."""
    from ait.store import Store

    store_path = data_dir / "store"
    if not store_path.exists():
        console.print("[yellow]No local store found.[/]")
        return

    store = Store(store_path)

    if graph:
        msg = f"Clear graph [bold]{graph}[/]?"
    else:
        msg = f"Clear [bold]all {len(store)} triples[/] from store?"

    if not force and not typer.confirm(msg):
        console.print("Cancelled.")
        return

    store.clear(graph)
    console.print("[green]Cleared.[/]")


@app.command()
def query(
    sparql: str = typer.Argument(..., help="SPARQL query to execute"),
    data_dir: Path = typer.Option(
        Path.home() / ".ait",
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum results to display",
    ),
) -> None:
    """Execute a SPARQL query against the local store."""
    import json

    from ait.store import Store

    store_path = data_dir / "store"
    if not store_path.exists():
        console.print("[red]No local store found.[/]")
        raise typer.Exit(1)

    store = Store(store_path)
    results = store.query(sparql)

    if not results:
        console.print("[yellow]No results.[/]")
        return

    console.print(json.dumps(results[:limit], indent=2))
    if len(results) > limit:
        console.print(f"[dim]... and {len(results) - limit} more[/]")


@app.command()
def web(
    data_dir: Path = typer.Option(
        Path.home() / ".ait",
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to run the web server on",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind to",
    ),
) -> None:
    """Start the web UI server."""
    import uvicorn

    from ait.web import app as web_app, configure

    configure(data_dir)

    console.print(f"[bold green]ait[/] v{__version__} web UI", style="dim")
    console.print(f"Data directory: {data_dir}", style="dim")
    console.print(f"Starting web server at http://{host}:{port}", style="dim")

    uvicorn.run(web_app, host=host, port=port)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"ait v{__version__}")


if __name__ == "__main__":
    app()
