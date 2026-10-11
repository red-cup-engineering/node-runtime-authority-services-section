#!/usr/bin/env python3
"""
RRPR Interface CLI - Command-line tools for the Relationing Research Program Repository.

One-shot operations for navigating, querying, and understanding the repository graph.
Thin wrapper around core operations - designed for agent accessibility.

The repository is the research. These tools help you explore it.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from rrpr import publish as publishing
from rrpr import query as rsc_query
from rrpr import runbook as runbook_lib
from rrp.authoring import draft_from_note, lint_paper, scaffold_paper
from rrp.config import DEFAULT_DB_PATH, get_default_config, set_active_db_path
from rrp.database import (
    CURRENT_INGESTOR_VERSION,
    CURRENT_SCHEMA_VERSION,
    Database,
    get_db_connection,
)
from rrp.git_extractor import GitExtractor
from rrp.ingestor import ingest_markdown_file

app = typer.Typer(
    name="rrpr",
    help="Relationing Research Program Repository Interface - Navigate the research as a knowledge graph",
    add_completion=False
)
console = Console()

publish_app = typer.Typer(help="Publish research documents (PDF/HTML/Markdown)")
app.add_typer(publish_app, name="publish")


def _sanitize_branch_name(name: str) -> str:
    safe_chars = []
    for char in name.strip():
        if char.isalnum() or char in ("-", "_", "."):
            safe_chars.append(char)
        else:
            safe_chars.append("-")
    sanitized = "".join(safe_chars).strip("-")
    return sanitized or "unknown"


def _collect_default_documents() -> List[Path]:
    roots = [Path("research/papers"), Path("txt/scientific-texts")]
    docs: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        docs.extend(sorted(root.rglob("*.md")))
    return docs


def _pick_seed_db(target: Path, candidates: List[Optional[Path]]) -> Optional[Path]:
    """Return the first usable seed database that is not the target itself."""
    for candidate in candidates:
        if not candidate:
            continue
        try:
            if candidate.resolve() == target.resolve():
                continue
        except FileNotFoundError:
            # resolve() fails if parent dirs missing; we only care if file exists
            pass
        if candidate.exists():
            return candidate
    return None


@publish_app.command("docs")
def publish_docs(
    formats: List[str] = typer.Option(
        ["pdf", "html"],
        "--format",
        "-f",
        case_sensitive=False,
        help="Output formats (supported: pdf, html)"
    ),
    out_dir: Path = typer.Option(
        Path("dist"),
        "--out",
        "-o",
        help="Directory where outputs will be written"
    ),
    docs: Optional[List[Path]] = typer.Option(
        None,
        "--doc",
        "-d",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Specific Markdown documents to publish"
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Dry run (default) or apply to actually generate files"
    )
):
    """Publish research documents to PDF/HTML bundles."""
    doc_paths = docs or _collect_default_documents()
    if not doc_paths:
        console.print("[yellow]No documents found to publish.[/yellow]")
        raise typer.Exit(1)

    doc_paths = list(dict.fromkeys(doc_paths))
    formats = [fmt.lower() for fmt in formats]

    console.print(f"[blue]Publishing {len(doc_paths)} docs in {formats} to {out_dir} (dry_run={dry_run})[/blue]")

    metadata = publishing.get_git_metadata()
    try:
        results = publishing.publish_documents(
            doc_paths,
            formats,
            out_dir,
            dry_run=dry_run,
            git_info=metadata,
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    manifest_dir = Path("docs/for-agents/reports")
    manifest_path = manifest_dir / f"publish-{timestamp}-{metadata['commit']}.json"
    publishing.write_manifest(
        results,
        manifest_path,
        extra={
            "branch": metadata["branch"],
            "commit": metadata["commit"],
            "formats": formats,
            "dry_run": dry_run
        }
    )

    table = Table(title="Publish Results", show_lines=True)
    table.add_column("Document", style="bright_cyan")
    table.add_column("Format")
    table.add_column("Status")
    table.add_column("Detail")

    for result in results:
        table.add_row(str(result.doc_path), result.format, result.status, result.detail)

    console.print(table)
    console.print(f"[green]Manifest:[/green] {manifest_path}")

# Maybe restructure to avoid duplicate names (publish_app used later). Remove this block to avoid redefinition? We'll add actual Typer below.


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


@ingest_app.command("rebuild")
def ingest_rebuild(
    source_dir: Path = typer.Option(
        Path("research/papers"),
        "--source", "-s",
        help="Directory containing papers to ingest"
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Skip automatic backup before rebuild"
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch", "-b",
        help="Git branch (auto-detected if not specified)"
    ),
    commit: Optional[str] = typer.Option(
        None,
        "--commit", "-c",
        help="Git commit hash (auto-detected if not specified)"
    )
):
    """
    Clean rebuild: backup database, wipe data, re-ingest all papers.
    
    This is a safe, atomic operation that:
    1. Creates a timestamped backup
    2. Initializes a fresh database
    3. Ingests all papers from the source directory
    4. Records ingestion metadata
    """
    config = get_default_config()
    db = Database(config.db_path)
    
    try:
        # Auto-detect Git metadata if not provided
        if branch is None or commit is None:
            try:
                extractor = GitExtractor()
                if branch is None:
                    branch = extractor.current_branch
                if commit is None:
                    commit = extractor.current_commit
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not auto-detect Git metadata: {e}")
                branch = branch or "unknown"
                commit = commit or "unknown"
        
        console.print(f"[blue]Rebuild Configuration:[/blue]")
        console.print(f"  Source directory: {source_dir}")
        console.print(f"  Database: {config.db_path}")
        console.print(f"  Branch: {branch}")
        console.print(f"  Commit: {commit}")
        console.print()
        
        # Step 1: Backup
        if not no_backup:
            console.print("[blue]Step 1/4: Creating backup...[/blue]")
            db.connect()
            backup_path = db.perform_backup()
            db.disconnect()
            console.print(f"[green]✓[/green] Backup created: {backup_path}")
        else:
            console.print("[yellow]Skipping backup (--no-backup flag set)[/yellow]")
        
        # Step 2: Initialize fresh database (temp file for atomicity)
        console.print("[blue]Step 2/4: Initializing fresh database...[/blue]")
        
        # Build new database alongside old one for atomic swap
        temp_db_path = config.db_path.with_suffix(".new")
        if temp_db_path.exists():
            temp_db_path.unlink()
        
        temp_db = Database(temp_db_path)
        temp_db.connect()
        temp_db.initialize_schema()
        
        # Register predicates
        from rrp.predicates import CORE_PREDICATES
        for predicate in CORE_PREDICATES.values():
            temp_db.register_predicate(
                name=predicate.name,
                description=predicate.description,
                domain=predicate.domain,
                range=predicate.range,
                category=predicate.category.value,
                inverse_of=predicate.inverse_of,
                is_core=predicate.is_core
            )
        console.print("[green]✓[/green] Database initialized")
        
        # Step 3: Ingest all papers (fail-fast on any error)
        console.print(f"[blue]Step 3/4: Ingesting papers from {source_dir}...[/blue]")
        
        if not source_dir.exists():
            console.print(f"[red]Error:[/red] Source directory not found: {source_dir}")
            temp_db.disconnect()
            temp_db_path.unlink()
            raise typer.Exit(1)
        
        papers = sorted(source_dir.glob("*.md"))
        if not papers:
            console.print(f"[yellow]Warning:[/yellow] No .md files found in {source_dir}")
        
        total_docs = 0
        total_terms = 0
        total_authors = 0
        total_edges = 0
        failed_papers = []
        
        # Set environment variable so ingest_markdown_file uses temp database
        import os
        old_db_path = os.environ.get("RSC_DB_PATH")
        os.environ["RSC_DB_PATH"] = str(temp_db_path)
        
        try:
            for paper in papers:
                console.print(f"  Ingesting: {paper.name}...", end="")
                try:
                    result = ingest_markdown_file(paper, branch=branch, commit_hash=commit)
                    total_docs += 1
                    total_terms += len(result.term_relcells)
                    total_authors += len(result.author_relcells)
                    total_edges += result.edges_created
                    console.print(" [green]✓[/green]")
                except Exception as e:
                    console.print(f" [red]✗[/red] {e}")
                    failed_papers.append((paper.name, str(e)))
        finally:
            # Restore original environment variable
            if old_db_path is not None:
                os.environ["RSC_DB_PATH"] = old_db_path
            elif "RSC_DB_PATH" in os.environ:
                del os.environ["RSC_DB_PATH"]
        
        # Fail if ANY papers failed to ingest
        if failed_papers:
            console.print()
            console.print(f"[red]✗ Rebuild failed:[/red] {len(failed_papers)} paper(s) failed to ingest")
            for paper_name, error in failed_papers:
                console.print(f"  - {paper_name}: {error}")
            console.print()
            console.print("[yellow]Database unchanged - old database preserved[/yellow]")
            temp_db.disconnect()
            temp_db_path.unlink()
            raise typer.Exit(1)
        
        console.print(f"[green]✓[/green] Ingested {total_docs} documents")
        console.print(f"  Terms: {total_terms}")
        console.print(f"  Authors: {total_authors}")
        console.print(f"  Edges: {total_edges}")
        
        # Step 4: Record ingestion state and swap databases atomically
        console.print("[blue]Step 4/4: Recording metadata and activating new database...[/blue]")
        temp_db.record_ingestion_state(
            branch=branch,
            commit_hash=commit,
            source=str(source_dir)
        )
        temp_db.disconnect()
        
        # Atomic swap: replace() is atomic on POSIX systems
        # It will overwrite the old file if it exists
        try:
            temp_db_path.replace(config.db_path)
        except Exception as e:
            console.print(f"[red]✗ Failed to activate new database:[/red] {e}")
            console.print(f"[yellow]New database preserved at:[/yellow] {temp_db_path}")
            console.print(f"[yellow]Old database unchanged at:[/yellow] {config.db_path}")
            raise typer.Exit(1)
        
        console.print("[green]✓[/green] New database activated")
        console.print()
        console.print("[green]✓ Rebuild complete![/green]")
        console.print(f"  {total_docs} papers ingested successfully")
        console.print(f"  {total_terms} terms, {total_authors} authors, {total_edges} edges")
        
    except Exception as e:
        console.print(f"[red]✗ Rebuild failed:[/red] {e}")
        if db.connection:
            db.disconnect()
        raise typer.Exit(1)


# === DATABASE MANAGEMENT COMMANDS ===

db_app = typer.Typer(help="Database backup, restore, and information")
app.add_typer(db_app, name="db")


@db_app.command("info")
def db_info():
    """Show database information and ingestion status."""
    config = get_default_config()
    
    if not config.db_path.exists():
        console.print(f"[yellow]Database not found:[/yellow] {config.db_path}")
        console.print("Run 'ingest rebuild' to initialize the database.")
        raise typer.Exit(1)
    
    db = Database(config.db_path)
    db.connect()
    
    try:
        # Get db_state info
        cursor = db.connection.execute("SELECT * FROM db_state WHERE id = 1")
        state = cursor.fetchone()
        
        if state:
            console.print("[blue]Database Information:[/blue]")
            console.print(f"  Location: {config.db_path}")
            console.print(f"  Schema Version: {state['schema_version']} (current: {CURRENT_SCHEMA_VERSION})")
            console.print(f"  Ingestor Version: {state['ingestor_version']}")
            console.print()
            console.print("[blue]Last Ingestion:[/blue]")
            console.print(f"  Branch: {state['last_ingested_branch'] or 'N/A'}")
            console.print(f"  Commit: {state['last_ingested_commit'] or 'N/A'}")
            console.print(f"  Source: {state['last_ingested_source'] or 'N/A'}")
            console.print(f"  Timestamp: {state['last_ingested_at'] or 'N/A'}")
        
        # Get statistics
        stats = db.get_stats()
        console.print()
        console.print("[blue]Content Statistics:[/blue]")
        console.print(f"  Total RelCells: {stats['total_relcells']}")
        console.print(f"  Files: {stats['file_relcells']}")
        console.print(f"  Virtual Cells: {stats['virtual_relcells']}")
        console.print(f"  Terms: {stats['total_terms']}")
        console.print(f"  Documents with metadata: {stats['documents_with_metadata']}")
        console.print(f"  Total Edges: {stats['total_edges']}")
        console.print(f"  Unique Predicates: {stats['unique_predicates']}")
        
    finally:
        db.disconnect()


@db_app.command("backup")
def db_backup(
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Backup directory")
):
    """Create a timestamped backup of the database."""
    config = get_default_config()
    
    if not config.db_path.exists():
        console.print(f"[red]Error:[/red] Database not found: {config.db_path}")
        raise typer.Exit(1)
    
    db = Database(config.db_path)
    db.connect()
    
    try:
        backup_dir = output_dir or (config.db_path.parent / "backups")
        backup_path = db.perform_backup(backup_dir=backup_dir)
        console.print(f"[green]✓ Backup created:[/green] {backup_path}")
    except Exception as e:
        console.print(f"[red]✗ Backup failed:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.disconnect()


@db_app.command("list-backups")
def db_list_backups(
    backup_dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Backup directory")
):
    """List available database backups."""
    backups = Database.list_backups(backup_dir=backup_dir)
    
    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return
    
    table = Table(title="Available Backups")
    table.add_column("Timestamp", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Size", justify="right")
    
    for backup_path, timestamp in backups:
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        table.add_row(
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            backup_path.name,
            f"{size_mb:.2f} MB"
        )
    
    console.print(table)


@db_app.command("restore")
def db_restore(
    backup_file: Path = typer.Argument(..., help="Path to backup file to restore")
):
    """Restore database from a backup file."""
    config = get_default_config()
    
    if not backup_file.exists():
        console.print(f"[red]Error:[/red] Backup file not found: {backup_file}")
        raise typer.Exit(1)
    
    console.print(f"[yellow]Warning:[/yellow] This will replace the current database!")
    console.print(f"  Current: {config.db_path}")
    console.print(f"  Backup: {backup_file}")
    
    confirm = typer.confirm("Continue with restore?")
    if not confirm:
        console.print("[yellow]Restore cancelled[/yellow]")
        raise typer.Exit(0)
    
    db = Database(config.db_path)
    
    try:
        db.restore_backup(backup_file)
        console.print(f"[green]✓ Database restored from:[/green] {backup_file}")
    except Exception as e:
        console.print(f"[red]✗ Restore failed:[/red] {e}")
        raise typer.Exit(1)


@db_app.command("switch")
def db_switch(
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name to bind the database to"),
    source: Optional[Path] = typer.Option(None, "--source", "-s", help="Optional database to copy from when creating the new branch database"),
):
    """
    Switch to a branch-specific database file (creates one if necessary).
    
    This allows agents on different branches to work with isolated SQLite files
    without coordinating. The active selection is stored in .rrpr-active-db.
    """
    config = get_default_config()

    if branch is None:
        try:
            extractor = GitExtractor()
            branch = extractor.current_branch
        except Exception:
            branch = "unknown"
            console.print("[yellow]Warning:[/yellow] Could not detect branch automatically.")

    safe_branch = _sanitize_branch_name(branch)
    target_dir = DEFAULT_DB_PATH.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target_db = target_dir / f"rsc.{safe_branch}.db"

    seed = _pick_seed_db(target_db, [source, config.db_path, DEFAULT_DB_PATH])
    created = False

    if not target_db.exists():
        if seed:
            shutil.copy2(seed, target_db)
            created = True
            console.print(f"[green]✓[/green] Copied database from {seed} -> {target_db}")
        else:
            db = Database(target_db)
            db.connect()
            db.initialize_schema()
            db.disconnect()
            created = True
            console.print(f"[green]✓[/green] Initialized new database at {target_db}")

    set_active_db_path(target_db)
    console.print(f"[blue]Active database:[/blue] {target_db}")
    if not created and target_db.exists():
        console.print("[green]✓[/green] Using existing branch database (no changes made)")

    console.print("[cyan]Tip:[/cyan] Override temporarily with `RSC_DB_PATH=/path/to/db python -m rrpr ...` if needed.")


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

# === AUTHORING COMMANDS ===

authoring_app = typer.Typer(help="Authoring helpers for thesis-centered RRPR papers")
app.add_typer(authoring_app, name="authoring")


@authoring_app.command("scaffold")
def authoring_scaffold(
    out_dir: Path = typer.Argument(..., help="Target directory under txt/scientific-texts/..."),
    doc_id: str = typer.Argument(..., help="Document id (lowercase, hyphen/dot)"),
    title: str = typer.Argument(..., help="Paper title"),
    status: str = typer.Option("draft", "--status", help="Status enum"),
    document_type: str = typer.Option("paper", "--type", help="Document type enum"),
    authors: Optional[str] = typer.Option(None, "--authors", help="Comma-separated authors"),
):
    """Create a new paper from the template with populated frontmatter."""
    try:
        author_list = [a.strip() for a in authors.split(",")] if authors else None
        created = scaffold_paper(
            out_dir=out_dir,
            doc_id=doc_id,
            title=title,
            status=status,
            document_type=document_type,
            authors=author_list,
        )
        console.print(f"[green]✓ Created:[/green] {created}")
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@authoring_app.command("lint")
def authoring_lint(
    file_path: Path = typer.Argument(..., help="Path to Markdown paper"),
):
    """Validate frontmatter and check for required structural sections."""
    result = lint_paper(file_path)
    if not result.ok:
        console.print(f"[red]✗ Frontmatter errors ({len(result.errors)}):[/red]")
        for e in result.errors:
            console.print(f"  - {e}")
    else:
        console.print("[green]✓ Frontmatter valid[/green]")

    if result.warnings:
        console.print(f"[yellow]Warnings ({len(result.warnings)}):[/yellow]")
        for w in result.warnings:
            console.print(f"  - {w}")

    if not result.ok:
        raise typer.Exit(1)


@authoring_app.command("from-note")
def authoring_from_note(
    note_path: Path = typer.Argument(..., help="Path to a research note"),
    out_dir: Path = typer.Argument(..., help="Target directory under txt/scientific-texts/..."),
    doc_id: str = typer.Argument(..., help="Document id for the draft"),
    title: Optional[str] = typer.Option(None, "--title", help="Override title"),
    no_source: bool = typer.Option(False, "--no-source", help="Do not write .source.org"),
):
    """Bootstrap a draft from a research note, preserving verbatim provenance."""
    try:
        paper, source = draft_from_note(
            note_path=note_path,
            out_dir=out_dir,
            doc_id=doc_id,
            title=title,
            include_source_as_appendix=not no_source,
        )
        console.print(f"[green]✓ Draft created:[/green] {paper}")
        if source:
            console.print(f"[green]✓ Source saved:[/green] {source}")
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


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


def _parse_key_values(pairs: List[str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected KEY=VALUE, got '{item}'")
        key, value = item.split("=", 1)
        values[key.strip()] = value.strip()
    return values


@app.command("run")
def run_runbook(
    runbook_path: Path = typer.Argument(..., help="Path to a YAML runbook"),
    apply: bool = typer.Option(False, "--apply", help="Apply runbook operations (default: dry-run)"),
    input_override: List[str] = typer.Option(
        [],
        "--input",
        "-i",
        help="Override runbook inputs (KEY=VALUE)",
    ),
    set_variable: List[str] = typer.Option(
        [],
        "--set",
        "-s",
        help="Set additional template variables (KEY=VALUE)",
    ),
):
    """
    Execute a YAML runbook (Issue-B harness).
    """
    runbook = runbook_lib.load_runbook(runbook_path)
    overrides = _parse_key_values(input_override)
    extra_vars = _parse_key_values(set_variable)
    try:
        runbook_lib.execute_runbook(
            runbook,
            runbook_path=runbook_path,
            apply=apply,
            input_overrides=overrides,
            set_variables=extra_vars,
            console=console,
        )
    except Exception as exc:
        console.print(f"[red]Runbook execution failed:[/red] {exc}")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
