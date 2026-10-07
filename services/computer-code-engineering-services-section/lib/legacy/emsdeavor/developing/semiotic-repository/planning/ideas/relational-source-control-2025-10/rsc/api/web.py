"""
HTML web interface endpoints.

These endpoints serve the browser-based UI for navigating
the repository knowledge graph.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path
import html

from rsc.database import get_db_connection
from rsc.api.utils import dict_factory

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>RRPR Interface - Relationing Research Program Repository</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .card {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat {
            display: inline-block;
            margin: 10px 20px;
            font-size: 1.2em;
        }
        .stat-value { font-weight: bold; color: #007bff; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        tr:hover { background: #f8f9fa; }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }
        .badge-virtual { background: #e7f3ff; color: #0066cc; }
        .badge-document { background: #e8f5e9; color: #2e7d32; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .nav {
            background: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .nav a {
            margin-right: 20px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <h1>🔗 RRPR Interface</h1>
    <p style="color: #666; margin-top: -10px; font-size: 0.95em;">Relationing Research Program Repository - Navigate the research as a knowledge graph</p>
    
    <div class="nav">
        <a href="#stats">Statistics</a>
        <a href="#files">Files</a>
        <a href="#commits">Commits</a>
        <a href="#documents">Documents</a>
        <a href="#terms">Terms</a>
        <a href="#authors">Authors</a>
        <a href="#citations">Citations</a>
        <a href="/api/docs">API Docs</a>
    </div>

    <div id="stats" class="card">
        <h2>Database Statistics</h2>
        <div id="stats-content">Loading...</div>
    </div>

    <div id="files" class="card">
        <h2>Repository Files</h2>
        <div id="files-content">Loading...</div>
    </div>

    <div id="commits" class="card">
        <h2>Git Commits</h2>
        <div id="commits-content">Loading...</div>
    </div>

    <div id="documents" class="card">
        <h2>Documents</h2>
        <div id="documents-content">Loading...</div>
    </div>

    <div id="terms" class="card">
        <h2>Terms</h2>
        <div id="terms-content">Loading...</div>
    </div>

    <div id="authors" class="card">
        <h2>Authors & Contributions</h2>
        <div id="authors-content">Loading...</div>
    </div>

    <div id="branches" class="card">
        <h2>Git Branches</h2>
        <div id="branches-content">Loading...</div>
    </div>

    <div id="citations" class="card">
        <h2>Citations</h2>
        <div id="citations-content">Loading...</div>
    </div>

    <script>
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stats-content').innerHTML = `
                <span class="stat">Documents: <span class="stat-value">${data.documents}</span></span>
                <span class="stat">Virtual Cells: <span class="stat-value">${data.virtual_cells}</span></span>
                <span class="stat">Edges: <span class="stat-value">${data.edges}</span></span>
                <span class="stat">Terms: <span class="stat-value">${data.terms}</span></span>
                <span class="stat">Authors: <span class="stat-value">${data.authors}</span></span>
            `;
        }

        async function loadDocuments() {
            const res = await fetch('/api/documents');
            const docs = await res.json();
            if (docs.length === 0) {
                document.getElementById('documents-content').innerHTML = '<p>No documents yet. Use the CLI to ingest Markdown files.</p>';
                return;
            }
            let html = '<table><tr><th>ID</th><th>Title</th><th>Path</th><th>Branch</th><th>Status</th></tr>';
            for (const doc of docs) {
                html += `<tr>
                    <td><a href="/api/documents/${doc.id}">${doc.id}</a></td>
                    <td>${doc.title || 'Untitled'}</td>
                    <td><code>${doc.path}</code></td>
                    <td>${doc.branch}</td>
                    <td><span class="badge badge-document">${doc.status || 'draft'}</span></td>
                </tr>`;
            }
            html += '</table>';
            document.getElementById('documents-content').innerHTML = html;
        }

        async function loadTerms() {
            const res = await fetch('/api/terms');
            const terms = await res.json();
            if (terms.length === 0) {
                document.getElementById('terms-content').innerHTML = '<p>No terms defined yet.</p>';
                return;
            }
            let html = '<table><tr><th>ID</th><th>Label</th><th>Description</th></tr>';
            for (const term of terms) {
                html += `<tr>
                    <td><code>${term.term_id}</code></td>
                    <td><strong>${term.label}</strong></td>
                    <td>${term.description || ''}</td>
                </tr>`;
            }
            html += '</table>';
            document.getElementById('terms-content').innerHTML = html;
        }

        async function loadAuthors() {
            const [docAuthors, gitAuthors] = await Promise.all([
                fetch('/api/authors').then(r => r.json()),
                fetch('/api/authors/contributions').then(r => r.json())
            ]);
            
            let html = '<h3>Document Authors</h3>';
            if (docAuthors.length === 0) {
                html += '<p>No document authors yet.</p>';
            } else {
                html += '<table><tr><th>ID</th><th>Name</th></tr>';
                for (const author of docAuthors) {
                    html += `<tr>
                        <td><code>${author.author_id}</code></td>
                        <td><strong>${author.name}</strong></td>
                    </tr>`;
                }
                html += '</table>';
            }
            
            html += '<h3 style="margin-top: 20px;">Git Contributors</h3>';
            if (gitAuthors.length === 0) {
                html += '<p>No Git contributors yet. Run <code>ingest-git-history</code>.</p>';
            } else {
                html += '<table><tr><th>Name</th><th>Commits</th></tr>';
                for (const author of gitAuthors) {
                    html += `<tr>
                        <td><strong>${author.name || 'Unknown'}</strong></td>
                        <td><span class="badge badge-virtual">${author.commit_count || 0} commits</span></td>
                    </tr>`;
                }
                html += '</table>';
            }
            
            document.getElementById('authors-content').innerHTML = html;
        }

        async function loadBranches() {
            const res = await fetch('/api/branches');
            const branches = await res.json();
            if (branches.length === 0) {
                document.getElementById('branches-content').innerHTML = '<p>No branches found. Run <code>ingest-git-history</code>.</p>';
                return;
            }
            let html = '<table><tr><th>Branch</th><th>Commits</th></tr>';
            for (const branch of branches) {
                html += `<tr>
                    <td><strong>${branch.name || 'Unknown'}</strong></td>
                    <td><span class="badge badge-document">${branch.commit_count || 0} commits</span></td>
                </tr>`;
            }
            html += '</table>';
            document.getElementById('branches-content').innerHTML = html;
        }

        async function loadCitations() {
            const res = await fetch('/api/citations');
            const citations = await res.json();
            if (citations.length === 0) {
                document.getElementById('citations-content').innerHTML = '<p>No citations found. Citations appear when documents reference other documents or external publications.</p>';
                return;
            }
            let html = '<table><tr><th>Source</th><th>Relation</th><th>Target</th></tr>';
            for (const cite of citations) {
                const source = cite.source_title || cite.source_path;
                const target = cite.target_title || cite.target_path || cite.object_literal || 'Unknown';
                html += `<tr>
                    <td><strong>${source}</strong></td>
                    <td><span class="badge badge-virtual">${cite.predicate}</span></td>
                    <td>${target}</td>
                </tr>`;
            }
            html += '</table>';
            document.getElementById('citations-content').innerHTML = html;
        }

        async function loadFiles() {
            const res = await fetch('/api/files?limit=50');
            const files = await res.json();
            if (files.length === 0) {
                document.getElementById('files-content').innerHTML = '<p>No files found. Run <code>ingest-repo</code> to scan repository.</p>';
                return;
            }
            let html = '<table><tr><th>Path</th><th>Type</th><th>Size</th><th>Branch</th></tr>';
            for (const file of files) {
                const size = file.size_bytes ? (file.size_bytes / 1024).toFixed(1) + ' KB' : '0 KB';
                html += `<tr>
                    <td><a href="/cell/${file.id}"><code>${file.path}</code></a></td>
                    <td><span class="badge badge-virtual">${file.file_type || 'unknown'}</span></td>
                    <td>${size}</td>
                    <td>${file.branch}</td>
                </tr>`;
            }
            html += '</table>';
            html += `<p style="margin-top: 15px; color: #666; font-size: 0.9em;">Showing first 50 files. Total: ${files.length}+</p>`;
            document.getElementById('files-content').innerHTML = html;
        }

        async function loadCommits() {
            const res = await fetch('/api/commits?limit=25');
            const commits = await res.json();
            if (commits.length === 0) {
                document.getElementById('commits-content').innerHTML = '<p>No commits found. Run <code>ingest-git-history</code> to extract commit history.</p>';
                return;
            }
            let html = '<table><tr><th>SHA</th><th>Message</th><th>Timestamp</th></tr>';
            for (const commit of commits) {
                const msg = commit.message ? (commit.message.length > 60 ? commit.message.substring(0, 60) + '...' : commit.message) : 'No message';
                const time = commit.timestamp ? new Date(commit.timestamp).toLocaleString() : 'Unknown';
                html += `<tr>
                    <td><code>${commit.sha}</code></td>
                    <td>${msg}</td>
                    <td>${time}</td>
                </tr>`;
            }
            html += '</table>';
            html += `<p style="margin-top: 15px; color: #666; font-size: 0.9em;">Showing recent 25 commits.</p>`;
            document.getElementById('commits-content').innerHTML = html;
        }

        loadStats();
        loadFiles();
        loadCommits();
        loadDocuments();
        loadTerms();
        loadAuthors();
        loadBranches();
        loadCitations();
    </script>
</body>
</html>
"""


@router.get("/cell/{cell_id}", response_class=HTMLResponse)
async def cell_viewer(cell_id: int):
    """Dedicated page for viewing a cell and its relationships."""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Get cell details
    cursor.execute("""
        SELECT 
            id, branch, commit_hash, path, file_type, mime_type, 
            size_bytes, checksum, differentiation_mode, is_virtual, ingested_at
        FROM relcells
        WHERE id = ?
    """, (cell_id,))
    
    cell = cursor.fetchone()
    if not cell:
        conn.close()
        return HTMLResponse("<h1>Cell not found</h1>", status_code=404)
    
    # Get edges FROM this cell
    cursor.execute("""
        SELECT 
            e.predicate, 
            e.object_literal, 
            r.path as object_path,
            r.id as object_id,
            r.is_virtual as object_is_virtual
        FROM edges e
        LEFT JOIN relcells r ON e.object_id = r.id
        WHERE e.subject_id = ?
        ORDER BY e.predicate
    """, (cell_id,))
    edges_from = cursor.fetchall()
    
    # Get edges TO this cell
    cursor.execute("""
        SELECT 
            e.predicate, 
            r.path as subject_path,
            r.id as subject_id,
            r.is_virtual as subject_is_virtual
        FROM edges e
        JOIN relcells r ON e.subject_id = r.id
        WHERE e.object_id = ?
        ORDER BY e.predicate
    """, (cell_id,))
    edges_to = cursor.fetchall()
    
    conn.close()
    
    # Read file contents (for non-virtual cells)
    file_content = None
    content_error = None
    if not cell['is_virtual']:
        try:
            file_path = Path(cell['path'])
            if file_path.exists():
                # Try to read as text
                try:
                    file_content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    content_error = "Binary file - cannot display content"
            else:
                content_error = "File not found on disk"
        except Exception as e:
            content_error = f"Error reading file: {str(e)}"
    
    # Build HTML components
    path_display = cell['path']
    file_type_badge = f'<span class="badge badge-virtual">{cell["file_type"] or "unknown"}</span>'
    size_display = f'{cell["size_bytes"] / 1024:.1f} KB' if cell["size_bytes"] else '0 KB'
    diff_mode_badge = f'<span class="badge badge-document">{cell["differentiation_mode"]}</span>'
    
    edges_html = ""
    if edges_from:
        edges_html += "<h3>Edges FROM this cell</h3><div class='edge-list'>"
        for edge in edges_from:
            if edge['object_literal']:
                edges_html += f"""
                    <div class='edge-item'>
                        <span class='edge-predicate'>{edge['predicate']}</span>: 
                        <code>{edge['object_literal']}</code>
                    </div>
                """
            else:
                obj_link = f"/cell/{edge['object_id']}" if edge['object_id'] else "#"
                edges_html += f"""
                    <div class='edge-item'>
                        <span class='edge-predicate'>{edge['predicate']}</span>: 
                        <a href='{obj_link}'><code>{edge['object_path']}</code></a>
                    </div>
                """
        edges_html += "</div>"
    
    if edges_to:
        edges_html += "<h3 style='margin-top: 30px;'>Edges TO this cell</h3><div class='edge-list'>"
        for edge in edges_to:
            subj_link = f"/cell/{edge['subject_id']}" if edge['subject_id'] else "#"
            edges_html += f"""
                <div class='edge-item'>
                    <a href='{subj_link}'><code>{edge['subject_path']}</code></a> 
                    <span class='edge-predicate'>{edge['predicate']}</span> this cell
                </div>
            """
        edges_html += "</div>"
    
    if not edges_from and not edges_to:
        edges_html = "<p style='color: #999;'>No edges connected to this cell.</p>"
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Cell {cell_id} - RRPR Interface</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        h1 {{ margin: 0 0 15px 0; color: #333; }}
        .back-link {{ color: #007bff; text-decoration: none; font-size: 14px; }}
        .back-link:hover {{ text-decoration: underline; }}
        .metadata {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metadata-row {{
            margin: 10px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .metadata-label {{
            font-weight: 600;
            color: #555;
            display: inline-block;
            width: 180px;
        }}
        .edges-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .badge-virtual {{ background: #e7f3ff; color: #0066cc; }}
        .badge-document {{ background: #e8f5e9; color: #2e7d32; }}
        .edge-list {{ margin-top: 15px; }}
        .edge-item {{
            padding: 12px;
            margin: 8px 0;
            background: #f8f9fa;
            border-left: 3px solid #007bff;
            border-radius: 4px;
        }}
        .edge-predicate {{
            font-weight: 600;
            color: #007bff;
        }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }}
        h3 {{ color: #333; margin-top: 20px; }}
        .content-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .file-content {{
            margin-top: 15px;
            max-height: 600px;
            overflow: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }}
        .file-content pre {{
            margin: 0;
            padding: 15px;
            background: #f8f9fa;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .content-error {{
            padding: 15px;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            margin-top: 15px;
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
</head>
<body>
    <div class="header">
        <a href="/" class="back-link">← Back to repository</a>
        <h1>Cell {cell_id}</h1>
        <code style="font-size: 1.1em;">{path_display}</code>
    </div>
    
    <div class="metadata">
        <h2>Metadata</h2>
        <div class="metadata-row">
            <span class="metadata-label">File Type:</span>
            {file_type_badge}
        </div>
        <div class="metadata-row">
            <span class="metadata-label">Differentiation Mode:</span>
            {diff_mode_badge}
        </div>
        <div class="metadata-row">
            <span class="metadata-label">Size:</span>
            <code>{size_display}</code>
        </div>
        <div class="metadata-row">
            <span class="metadata-label">Branch:</span>
            <code>{cell['branch']}</code>
        </div>
        <div class="metadata-row">
            <span class="metadata-label">Commit:</span>
            <code>{cell['commit_hash'][:12]}</code>
        </div>
        <div class="metadata-row">
            <span class="metadata-label">Ingested:</span>
            <code>{cell['ingested_at']}</code>
        </div>
    </div>
    
    <div class="content-section">
        <h2>File Content</h2>
        {f'''
        <div class="file-content">
            <pre><code class="language-{cell["file_type"] or "plaintext"}">{html.escape(file_content)}</code></pre>
        </div>
        <script>hljs.highlightAll();</script>
        ''' if file_content is not None else f'<div class="content-error">{content_error or "Virtual cell - no file content"}</div>'}
    </div>
    
    <div class="edges-section">
        <h2>Relationships</h2>
        {edges_html}
    </div>
</body>
</html>
"""
