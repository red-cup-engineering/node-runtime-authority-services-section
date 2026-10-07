#!/usr/bin/env python3
"""
DEPRECATED: This CLI is deprecated in favor of the new Typer-based CLI.

Please use `cli.py` instead:
  python3 cli.py --help
  python3 cli.py stats
  python3 cli.py ingest repo
  python3 cli.py query neighbors <id>

This file is kept temporarily for backward compatibility but will be removed.

===== OLD ARGPARSE CLI (DEPRECATED) =====
"""

print("\n⚠️  WARNING: rsc_cli.py is deprecated!")
print("   Please use the new CLI instead: python3 cli.py --help\n")

import sys
import argparse
from pathlib import Path
import sqlite3

from rsc.ingestor import ingest_markdown_file
from rsc.database import init_database, get_db_connection
from rsc.git_extractor import GitExtractor


def cmd_ingest(args):
    """Ingest a Markdown file."""
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.suffix == '.md':
        print(f"Error: Only Markdown files (.md) are supported")
        sys.exit(1)
    
    print(f"Ingesting: {file_path}")
    
    try:
        result = ingest_markdown_file(
            file_path,
            branch=args.branch,
            commit_hash=args.commit
        )
        
        print(f"✅ Success!")
        print(f"   Document RelCell ID: {result.document_relcell_id}")
        print(f"   Terms created: {len(result.term_relcells)}")
        print(f"   Authors created: {len(result.author_relcells)}")
        print(f"   Edges created: {result.edges_created}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_ingest_repo(args):
    """Ingest all files from repository."""
    print("🔍 Scanning repository for files...")
    
    try:
        extractor = GitExtractor()
        files, edges = extractor.ingest_repository_files(
            branch=args.branch,
            commit_hash=args.commit
        )
        
        print(f"✅ Repository ingestion complete!")
        print(f"   Files ingested: {files}")
        print(f"   Edges created: {edges}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_ingest_git_history(args):
    """Ingest Git commit history."""
    print("📜 Extracting Git commit history...")
    
    try:
        extractor = GitExtractor()
        commits, edges = extractor.ingest_commit_history(
            branch=args.branch,
            max_commits=args.max_commits
        )
        
        print(f"✅ Git history ingestion complete!")
        print(f"   Commits ingested: {commits}")
        print(f"   Edges created: {edges}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_stats(args):
    """Show database statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 0")
    docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relcells WHERE is_virtual = 1")
    virtual = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM edges")
    edges = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM terms")
    terms = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM authors")
    authors = cursor.fetchone()[0]
    
    conn.close()
    
    print("📊 Database Statistics")
    print(f"   Documents: {docs}")
    print(f"   Virtual Cells: {virtual}")
    print(f"   Edges: {edges}")
    print(f"   Terms: {terms}")
    print(f"   Authors: {authors}")


def cmd_list_documents(args):
    """List all documents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.id,
            r.branch,
            r.path,
            m.title,
            m.status
        FROM relcells r
        LEFT JOIN document_metadata m ON r.id = m.relcell_id
        WHERE r.is_virtual = 0
        ORDER BY r.ingested_at DESC
    """)
    
    docs = cursor.fetchall()
    conn.close()
    
    if not docs:
        print("No documents found.")
        return
    
    print(f"📄 {len(docs)} Documents:")
    for doc in docs:
        title = doc[3] or 'Untitled'
        status = doc[4] or 'draft'
        print(f"   [{doc[0]}] {title} ({status})")
        print(f"        {doc[1]}:{doc[2]}")


def cmd_list_terms(args):
    """List all terms."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT term_id, label, description
        FROM v_term_definitions
        ORDER BY label
    """)
    
    terms = cursor.fetchall()
    conn.close()
    
    if not terms:
        print("No terms found.")
        return
    
    print(f"🔤 {len(terms)} Terms:")
    for term in terms:
        desc = term[2][:60] + "..." if term[2] and len(term[2]) > 60 else term[2] or ""
        print(f"   {term[0]}: {term[1]}")
        if desc:
            print(f"      {desc}")


def cmd_list_authors(args):
    """List all authors."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT author_id, name, virtual_path
        FROM v_authors
        ORDER BY name
    """)
    
    authors = cursor.fetchall()
    conn.close()
    
    if not authors:
        print("No authors found.")
        return
    
    print(f"✍️  {len(authors)} Authors:")
    for author in authors:
        print(f"   {author[0]}: {author[1]}")
        print(f"      {author[2]}")


def cmd_list_files(args):
    """List all files (including non-documents)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, branch, commit_hash, path, file_type, size_bytes
        FROM relcells
        WHERE is_virtual = 0
        ORDER BY path
        LIMIT 100
    """)
    
    files = cursor.fetchall()
    conn.close()
    
    if not files:
        print("No files found.")
        return
    
    print(f"📁 {len(files)} Files:")
    for f in files:
        size = f[5] if f[5] else 0
        print(f"   [{f[0]}] {f[3]}")
        print(f"      Type: {f[4] or 'unknown'}, Size: {size} bytes")


def cmd_list_commits(args):
    """List all commits."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.path, e.object_literal
        FROM relcells r
        LEFT JOIN edges e ON e.subject_id = r.id AND e.predicate = 'commit_message'
        WHERE r.is_virtual = 1 AND r.path LIKE 'virtual:commit:%'
        ORDER BY r.ingested_at DESC
        LIMIT 50
    """)
    
    commits = cursor.fetchall()
    conn.close()
    
    if not commits:
        print("No commits found. Run 'ingest-git-history' to extract commit data.")
        return
    
    print(f"📜 {len(commits)} Commits:")
    for commit in commits:
        sha = commit[1].replace('virtual:commit:', '')[:8]
        message = commit[2][:60] + "..." if commit[2] and len(commit[2]) > 60 else commit[2] or ""
        print(f"   [{sha}] {message}")


def main():
    parser = argparse.ArgumentParser(
        description="RSC CLI - Relational Source Control",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest a Markdown file')
    ingest_parser.add_argument('file', help='Path to Markdown file')
    ingest_parser.add_argument('--branch', default='main', help='Git branch (default: main)')
    ingest_parser.add_argument('--commit', default='HEAD', help='Git commit hash (default: HEAD)')
    
    # Ingest-repo command
    ingest_repo_parser = subparsers.add_parser('ingest-repo', help='Ingest all repository files')
    ingest_repo_parser.add_argument('--branch', default=None, help='Git branch (default: current)')
    ingest_repo_parser.add_argument('--commit', default=None, help='Git commit hash (default: HEAD)')
    
    # Ingest-git-history command
    ingest_history_parser = subparsers.add_parser('ingest-git-history', help='Ingest Git commit history')
    ingest_history_parser.add_argument('--branch', default=None, help='Git branch (default: current)')
    ingest_history_parser.add_argument('--max-commits', type=int, default=None, help='Max commits to process')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List entities')
    list_parser.add_argument('entity', choices=['documents', 'terms', 'authors', 'files', 'commits'], 
                           help='Entity type to list')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize database if it doesn't exist
    db_path = Path("rsc.db")
    if not db_path.exists():
        print("Initializing database...")
        init_database(db_path)
    
    # Execute command
    if args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'ingest-repo':
        cmd_ingest_repo(args)
    elif args.command == 'ingest-git-history':
        cmd_ingest_git_history(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'list':
        if args.entity == 'documents':
            cmd_list_documents(args)
        elif args.entity == 'terms':
            cmd_list_terms(args)
        elif args.entity == 'authors':
            cmd_list_authors(args)
        elif args.entity == 'files':
            cmd_list_files(args)
        elif args.entity == 'commits':
            cmd_list_commits(args)


if __name__ == '__main__':
    main()
