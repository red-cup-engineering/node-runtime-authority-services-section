#!/usr/bin/env python3
"""
RRPR Interface CLI - Command-line tools for the Relationing Research Program Repository.

One-shot operations for navigating, querying, and understanding the repository graph.
Thin wrapper around core operations - designed for agent accessibility.

The repository is the research. These tools help you explore it.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from pathlib import Path
from typing import Optional, List
import sys

from rsc.database import get_db_connection
from rsc.ingestor import ingest_markdown_file
from rsc.git_extractor import GitExtractor
from rsc import query as rsc_query

app = typer.Typer(
    name="rrpr",
    help="Relationing Research Program Repository Interface - Navigate the research as a knowledge graph",
    add_completion=False
)
console = Console()


# === INGESTION COMMANDS ===

ingest_app = typer.Typer(help="Ingest files and Git metadata into the repository graph")
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("file")
def ingest_file(
    file_path: Path = typer.Argument(..., help="Path to Markdown file"),
    branch: str = typer.Option("refactor/2025-11", "--branch", "-b", help="Git branch name"),
    commit: str = typer.Option("HEAD", "--commit", "-c", help="Git commit hash")
):
    """Ingest a single Markdown file into the database."""
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)
    
    if file_path.suffix != '.md':
        console.print(f"[red]Error:[/red] Only Markdown files (.md) are supported")
        raise typer.Exit(1)
    
    console.print(f"[blue]Ingesting:[/blue] {file_path}")
    
    try:
        result = ingest_markdown_file(file_path, branch=branch, commit_hash=commit)
        
        console.print("[green]✓ Success![/green]")
        console.print(f"  Document RelCell ID: {result.document_relcell_id}")
        console.print(f"  Terms created: {len(result.term_relcells)}")
        console.print(f"  Authors created: {len(result.author_relcells)}")
        console.print(f"  Edges created: {result.edges_created}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@ingest_app.command("repo")
def ingest_repo(
    branch: str = typer.Option("refactor/2025-11", "--branch", "-b", help="Git branch name"),
    commit: str = typer.Option("HEAD", "--commit", "-c", help="Git commit hash")
):
    """Ingest all repository files into the database."""
    console.print("[blue]Scanning repository for files...[/blue]")
    
    try:
        extractor = GitExtractor()
        files, edges = extractor.ingest_repository_files(branch=branch, commit_hash=commit)
        
        console.print("[green]✓ Repository ingestion complete![/green]")
        console.print(f"  Files ingested: {files}")
        console.print(f"  Edges created: {edges}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@ingest_app.command("git-history")
def ingest_git_history(
    branch: str = typer.Option("refactor/2025-11", "--branch", "-b", help="Git branch name"),
    max_commits: Optional[int] = typer.Option(None, "--max-commits", help="Maximum commits to ingest")
):
    """Ingest Git commit history into the database."""
    console.print("[blue]Extracting Git commit history...[/blue]")
    
    try:
        extractor = GitExtractor()
        commits, edges = extractor.ingest_commit_history(branch=branch, max_commits=max_commits)
        
        console.print("[green]✓ Git history ingestion complete![/green]")
        console.print(f"  Commits ingested: {commits}")
        console.print(f"  Edges created: {edges}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


# === QUERY COMMANDS ===

query_app = typer.Typer(help="Query the knowledge graph")
app.add_typer(query_app, name="query")


@query_app.command("path")
def query_path(
    from_id: int = typer.Argument(..., help="Starting cell ID"),
    to_id: int = typer.Argument(..., help="Target cell ID"),
    max_hops: int = typer.Option(5, "--max-hops", help="Maximum path length"),
    predicates: Optional[str] = typer.Option(None, "--predicates", "-p", help="Comma-separated predicates to follow")
):
    """Find shortest path(s) between two cells."""
    conn = get_db_connection()
    try:
        predicate_list = predicates.split(",") if predicates else None
        paths = rsc_query.find_path(conn, from_id, to_id, max_hops, predicate_list)
        
        if not paths:
            console.print(f"[yellow]No path found between cells {from_id} and {to_id}[/yellow]")
            return
        
        console.print(f"[green]Found {len(paths)} path(s):[/green]")
        for i, path in enumerate(paths, 1):
            console.print(f"\nPath {i} (length {path['length']}):")
            console.print(f"  Cells: {' → '.join(map(str, path['cells']))}")
            
    finally:
        conn.close()


@query_app.command("traverse")
def query_traverse(
    start_id: int = typer.Argument(..., help="Starting cell ID"),
    max_depth: int = typer.Option(3, "--max-depth", "-d", help="Maximum traversal depth"),
    direction: str = typer.Option("outgoing", "--direction", help="Traversal direction (outgoing/incoming/both)"),
    predicates: Optional[str] = typer.Option(None, "--predicates", "-p", help="Comma-separated predicates to follow")
):
    """Traverse the graph from a starting cell."""
    if direction not in ("outgoing", "incoming", "both"):
        console.print("[red]Error:[/red] direction must be outgoing, incoming, or both")
        raise typer.Exit(1)
    
    conn = get_db_connection()
    try:
        predicate_list = predicates.split(",") if predicates else None
        result = rsc_query.traverse(conn, start_id, predicate_list, max_depth, direction)
        
        console.print(f"[green]Traversal from cell {start_id}:[/green]")
        console.print(f"  Cells reached: {len(result['cells'])}")
        console.print(f"  Edges traversed: {len(result['edges'])}")
        console.print(f"  Max depth: {max_depth}")
        console.print(f"  Direction: {direction}")
        
    finally:
        conn.close()


@query_app.command("neighbors")
def query_neighbors(
    cell_id: int = typer.Argument(..., help="Cell ID"),
    direction: str = typer.Option("both", "--direction", help="Direction (outgoing/incoming/both)"),
    predicates: Optional[str] = typer.Option(None, "--predicates", "-p", help="Comma-separated predicates filter")
):
    """Show immediate neighbors (1-hop) of a cell."""
    if direction not in ("outgoing", "incoming", "both"):
        console.print("[red]Error:[/red] direction must be outgoing, incoming, or both")
        raise typer.Exit(1)
    
    conn = get_db_connection()
    try:
        predicate_list = predicates.split(",") if predicates else None
        result = rsc_query.neighbors(conn, cell_id, direction, predicate_list)
        
        neighbor_count = len(result['cells']) - 1  # Exclude starting cell
        console.print(f"[green]Cell {cell_id} has {neighbor_count} neighbor(s):[/green]")
        
        for cell in result['cells']:
            if cell['id'] != cell_id:
                console.print(f"  [{cell['id']}] {cell['path']} ({cell['differentiation_mode']})")
                
    finally:
        conn.close()


@query_app.command("orphans")
def query_orphans(
    min_edges: int = typer.Option(0, "--min-edges", help="Cells with <= this many edges")
):
    """Find cells with few or no edges (isolated entities)."""
    conn = get_db_connection()
    try:
        orphans = rsc_query.find_orphans(conn, min_edges)
        
        if not orphans:
            console.print(f"[green]No orphaned cells found (all cells have > {min_edges} edge(s))[/green]")
            return
        
        console.print(f"[yellow]Found {len(orphans)} orphaned cell(s):[/yellow]")
        for cell in orphans:
            console.print(f"  [{cell['id']}] {cell['path']} - {cell['edge_count']} edge(s)")
            
    finally:
        conn.close()


@query_app.command("cycles")
def query_cycles(
    predicate: str = typer.Argument(..., help="Predicate to check for cycles"),
    max_length: int = typer.Option(10, "--max-length", help="Maximum cycle length to detect")
):
    """Detect cycles for a specific predicate."""
    conn = get_db_connection()
    try:
        cycles = rsc_query.detect_cycles(conn, predicate, max_length)
        
        if not cycles:
            console.print(f"[green]No cycles detected for predicate '{predicate}' (stable structure)[/green]")
            return
        
        console.print(f"[yellow]Found {len(cycles)} cycle(s) for predicate '{predicate}':[/yellow]")
        for i, cycle in enumerate(cycles, 1):
            console.print(f"  Cycle {i}: {' → '.join(map(str, cycle))} → {cycle[0]}")
            
    finally:
        conn.close()


# === LIST COMMANDS ===

list_app = typer.Typer(help="List entities in the database")
app.add_typer(list_app, name="list")


@list_app.command("documents")
def list_documents():
    """List all Markdown documents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT path, id FROM relcells 
        WHERE is_virtual = 0 AND path LIKE '%.md'
        ORDER BY path
    """)
    
    table = Table(title="Documents")
    table.add_column("ID", style="cyan")
    table.add_column("Path", style="green")
    
    for path, cell_id in cursor.fetchall():
        table.add_row(str(cell_id), path)
    
    console.print(table)
    conn.close()


@list_app.command("files")
def list_files(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum files to display")
):
    """List all repository files."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT path, id, differentiation_mode FROM relcells 
        WHERE is_virtual = 0
        ORDER BY path
        LIMIT ?
    """, (limit,))
    
    table = Table(title=f"Files (showing up to {limit})")
    table.add_column("ID", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Mode", style="yellow")
    
    for path, cell_id, mode in cursor.fetchall():
        table.add_row(str(cell_id), path, mode)
    
    console.print(table)
    conn.close()


@list_app.command("terms")
def list_terms():
    """List all defined terms."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.path, r.id,
               (SELECT e.object_literal FROM edges e 
                WHERE e.subject_id = r.id AND e.predicate = 'has_label' LIMIT 1) as label
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:term:%'
        ORDER BY r.path
    """)
    
    table = Table(title="Terms")
    table.add_column("ID", style="cyan")
    table.add_column("Term ID", style="magenta")
    table.add_column("Label", style="green")
    
    for path, cell_id, label in cursor.fetchall():
        term_id = path.replace("virtual:term:", "")
        table.add_row(str(cell_id), term_id, label or "")
    
    console.print(table)
    conn.close()


@list_app.command("authors")
def list_authors():
    """List all authors."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.path, r.id
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:author:%'
        ORDER BY r.path
    """)
    
    table = Table(title="Authors")
    table.add_column("ID", style="cyan")
    table.add_column("Author", style="green")
    
    for path, cell_id in cursor.fetchall():
        author_name = path.replace("virtual:author:", "")
        table.add_row(str(cell_id), author_name)
    
    console.print(table)
    conn.close()


@list_app.command("commits")
def list_commits(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum commits to display")
):
    """List Git commits."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.path, r.id,
               (SELECT e.object_literal FROM edges e 
                WHERE e.subject_id = r.id AND e.predicate = 'has_message' LIMIT 1) as message
        FROM relcells r
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:commit:%'
        ORDER BY r.id DESC
        LIMIT ?
    """, (limit,))
    
    table = Table(title=f"Commits (showing up to {limit})")
    table.add_column("ID", style="cyan")
    table.add_column("Commit Hash", style="yellow")
    table.add_column("Message", style="green")
    
    for path, cell_id, message in cursor.fetchall():
        commit_hash = path.replace("virtual:commit:", "")[:8]
        msg_preview = (message[:60] + "...") if message and len(message) > 60 else (message or "")
        table.add_row(str(cell_id), commit_hash, msg_preview)
    
    console.print(table)
    conn.close()


# === STATS COMMAND ===

@app.command()
def stats():
    """Show database statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 0")
    files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1")
    virtual = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM edges")
    edges = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1 AND path LIKE 'virtual:term:%'")
    terms = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1 AND path LIKE 'virtual:author:%'")
    authors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1 AND path LIKE 'virtual:commit:%'")
    commits = cursor.fetchone()[0]
    
    conn.close()
    
    table = Table(title="Repository Graph Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    
    table.add_row("Files (Git)", str(files))
    table.add_row("Virtual Cells", str(virtual))
    table.add_row("  ├─ Terms", str(terms))
    table.add_row("  ├─ Authors", str(authors))
    table.add_row("  └─ Commits", str(commits))
    table.add_row("Edges (Relations)", str(edges))
    
    console.print(table)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
