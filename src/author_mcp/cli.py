"""Command Line Interface for Author-MCP and ATC."""

from __future__ import annotations

import asyncio
import click
from rich.console import Console
from rich.table import Table
import uvicorn

from author_mcp import __version__
from author_mcp.atc import AuthorATC
from author_mcp.config import settings
from author_mcp.indexer import KnowledgeIndexer
from author_mcp.runbooks.service import RunbookService
from author_mcp.session import SessionManager

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="author-mcp")
def cli():
    """Author-MCP: Enterprise Knowledge Engine & Air Traffic Control CLI."""
    pass


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Force reindexing of all documents")
def index(force: bool):
    """Execute enterprise indexing pipeline across Books and Author text documents."""
    indexer = KnowledgeIndexer()
    with console.status("[bold green]Executing indexing pipeline..."):
        res = indexer.scan_and_index(force=force)

    table = Table(title="Author Knowledgebase Indexing Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Status", res.get("status", "unknown"))
    table.add_row("Files Indexed", str(res.get("indexed_count", 0)))
    table.add_row("Chunks Created", str(res.get("chunks_created", 0)))
    table.add_row("Total Active Documents", str(res.get("total_documents", 0)))
    table.add_row("Total Chunks", str(res.get("total_chunks", 0)))
    table.add_row("Partitioned Indices", ", ".join(res.get("indices", [])))
    console.print(table)


@cli.command()
def indices():
    """List all partitioned knowledge indices and document counts."""
    indexer = KnowledgeIndexer()
    table = Table(title="Partitioned Knowledge Indices")
    table.add_column("Index Name", style="bold cyan")
    table.add_column("Docs", style="green")
    table.add_column("Chunks", style="yellow")
    table.add_column("Bytes", style="magenta")
    table.add_column("Description", style="white")

    for info in indexer.storage.list_indices():
        table.add_row(
            info.name,
            str(info.document_count),
            str(info.chunk_count),
            f"{info.total_bytes / 1024:.1f} KB",
            info.description,
        )
    console.print(table)


@cli.command()
def runbooks():
    """List standard operating procedures (SOPs) and runbooks."""
    svc = RunbookService()
    table = Table(title="Author Operational Runbooks")
    table.add_column("ID", style="bold cyan")
    table.add_column("Title", style="green")
    table.add_column("Safety", style="yellow")
    table.add_column("Tags", style="dim")

    for r in svc.list_runbooks():
        table.add_row(r.name, r.title, r.safety_level, ", ".join(r.tags))
    console.print(table)


@cli.command()
def atc():
    """Display Air Traffic Control (ATC) status for Author suite."""
    controller = AuthorATC()
    status = controller.get_atc_status()

    table = Table(title="Author Suite — Air Traffic Control (ATC)")
    table.add_column("Subsystem", style="cyan")
    table.add_column("Property", style="yellow")
    table.add_column("Status", style="green")

    table.add_row("Suite", "Name", status.get("suite", "Author"))
    table.add_row("Tower", "Role", status.get("atc_role", "Root MCP & ATC"))
    table.add_row("Tower", "Network", status.get("control_tower", {}).get("network", "author-net"))

    mcp_m = status.get("members", {}).get("mcp", {})
    table.add_row("Member: mcp", "Hath0r Aligned", "[green]YES[/green]" if mcp_m.get("hathor_aligned") else "[red]NO[/red]")
    table.add_row("Member: mcp", "Git Branch", str(mcp_m.get("git", {}).get("branch", "unknown")))

    books_m = status.get("members", {}).get("books", {})
    table.add_row("Member: Books", "Hath0r Aligned", "[green]YES[/green]" if books_m.get("hathor_aligned") else "[red]NO[/red]")
    table.add_row("Member: Books", "Git Branch", str(books_m.get("git", {}).get("branch", "unknown")))
    table.add_row("Member: Books", "Site-Free (Text Only)", "[green]YES[/green]" if books_m.get("site_free") else "[red]SITE DETECTED[/red]")

    console.print(table)


@cli.command()
def sources():
    """List all configured knowledge sources and document counts."""
    indexer = KnowledgeIndexer()
    summary = indexer.get_sources_summary()
    table = Table(title="Author Knowledge Metrics")
    table.add_column("Metric / Index", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_row("Total Parent Documents", str(summary.get("total_documents", 0)))
    table.add_row("Total Indexed Chunks", str(summary.get("total_chunks", 0)))
    for idx_name, count in summary.get("indices", {}).items():
        table.add_row(f"Index ({idx_name})", str(count))
    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--index", "-i", "index_name", default=None, help="Target index filter")
@click.option("--category", "-c", default=None, help="Category filter")
@click.option("--limit", "-l", default=5, help="Number of results")
def search(query: str, index_name: str | None, category: str | None, limit: int):
    """Search author knowledgebase with BM25 ranking."""
    indexer = KnowledgeIndexer()
    results = indexer.search(query=query, index_name=index_name, category=category, limit=limit)
    if not results:
        console.print("[yellow]No matching documents found.[/yellow]")
        return

    table = Table(title=f"Search Results for: '{query}'")
    table.add_column("Score", style="green", width=8)
    table.add_column("Index", style="cyan", width=12)
    table.add_column("Title", style="bold white", width=25)
    table.add_column("Words", style="yellow", width=8)
    table.add_column("Preview", width=40)

    for r in results:
        table.add_row(
            f"{r['score']:.2f}",
            r["index"],
            r["title"],
            str(r.get("word_count", 0)),
            r["preview"][:60] + "...",
        )
    console.print(table)


@cli.command(name="sync-knowledge")
@click.option("--target", "-t", default=None, help="Custom target directory")
def sync_knowledge_cmd(target: str | None):
    """Synchronize indexed knowledgebase into .hath0r/knowledgebase single source of truth."""
    from pathlib import Path
    indexer = KnowledgeIndexer()
    target_path = Path(target) if target else None
    with console.status("[bold green]Synchronizing knowledgebase to .hath0r/knowledgebase..."):
        res = indexer.sync_to_hathor_knowledgebase(target_dir=target_path)

    table = Table(title="Hath0r Knowledgebase Synchronization")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Status", res.get("status", "unknown"))
    table.add_row("Documents Synced", str(res.get("documents_synced", 0)))
    table.add_row("Target Directory", res.get("target_directory", ""))
    console.print(table)


@cli.command()
def doctor():
    """Run health checks on Books path, storage, and Redis."""
    async def _check():
        indexer = KnowledgeIndexer()
        session_mgr = SessionManager()
        redis_ok = await session_mgr.ping()
        await session_mgr.close()
        stats = indexer.storage.get_stats()

        table = Table(title="Author-MCP System Doctor")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="white")

        table.add_row(
            "Books Repository Directory",
            "[green]PASS[/green]" if settings.BOOKS_DIR.exists() else "[red]NOT FOUND[/red]",
            str(settings.BOOKS_DIR),
        )
        table.add_row(
            "Books Site-Free Check (Text Only)",
            "[green]PASS[/green]" if not (settings.BOOKS_DIR / "site").exists() else "[red]SITE DIRECTORY FOUND[/red]",
            "No site directory present",
        )
        table.add_row(
            "Author-Sessions Redis",
            "[green]PASS[/green]" if redis_ok else "[yellow]UNREACHABLE (Optional outside Docker)[/yellow]",
            settings.REDIS_URL,
        )
        table.add_row(
            "Multi-Index Storage Directory",
            "[green]PASS[/green]",
            str(indexer.storage.base_dir),
        )
        table.add_row(
            "Partitioned Indices Count",
            "[green]PASS[/green]",
            str(len(stats.indices)),
        )
        table.add_row(
            "Indexed Documents Count",
            "[green]PASS[/green]",
            str(stats.total_documents),
        )
        console.print(table)

    asyncio.run(_check())


@cli.command()
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def serve(host: str | None, port: int | None):
    """Start the Author-MCP FastAPI server."""
    h = host or settings.HOST
    p = port or settings.PORT
    uvicorn.run("author_mcp.server:app", host=h, port=p, reload=False)


if __name__ == "__main__":
    cli()
