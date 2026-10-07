import asyncio
import os
import requests
import psycopg2
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

STORAGE_URL = os.environ.get("RDF_STORAGE_URL", "http://localhost:3000")

server = Server("rdf-knowledge-graph")

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="rdf://graphs/default",
            name="Default RDF Graph",
            mimeType="text/turtle",
            description="The main RDF graph containing all data and ontologies"
        ),
        Resource(
            uri="rdf://graphs/inference",
            name="Inference Graph",
            mimeType="text/turtle",
            description="Inferred triples from OWL reasoning"
        ),
        Resource(
            uri="rdf://graphs/validation",
            name="Validation Graph",
            mimeType="text/turtle",
            description="SHACL validation reports"
        ),
        Resource(
            uri="rdf://blog-posts",
            name="Blog Posts",
            mimeType="application/json",
            description="All blog posts in the knowledge graph"
        ),
        Resource(
            uri="rdf://ontologies",
            name="Ontologies",
            mimeType="text/turtle",
            description="Available ontologies and vocabularies"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("rdf://graphs/"):
        graph_name = uri.split("/")[-1]
        response = requests.get(f"{STORAGE_URL}/graphs/{graph_name}")
        if response.status_code == 200:
            data = response.json()
            triples_text = "\n".join([
                f"{t['subject']} {t['predicate']} {t['object']} ."
                for t in data.get("triples", [])
            ])
            return f"# {graph_name.title()} Graph ({data.get('size', 0)} triples)\n\n{triples_text}"
        return f"Error fetching graph: {response.status_code}"
    
    elif uri == "rdf://blog-posts":
        query = """
            SELECT ?post ?title ?author ?content ?published
            WHERE {
                ?post a <http://example.org/BlogPost> .
                OPTIONAL { ?post <http://example.org/hasTitle> ?title }
                OPTIONAL { ?post <http://example.org/hasAuthor> ?author }
                OPTIONAL { ?post <http://example.org/hasContent> ?content }
                OPTIONAL { ?post <http://example.org/publishedAt> ?published }
            }
        """
        response = requests.post(f"{STORAGE_URL}/sparql", json={"query": query})
        if response.status_code == 200:
            results = response.json()
            posts = []
            for binding in results.get("results", {}).get("bindings", []):
                post = {
                    "uri": binding.get("post", {}).get("value", ""),
                    "title": binding.get("title", {}).get("value", "Untitled"),
                    "author": binding.get("author", {}).get("value", "Unknown"),
                    "content": binding.get("content", {}).get("value", ""),
                    "published": binding.get("published", {}).get("value", "")
                }
                posts.append(post)
            import json
            return json.dumps(posts, indent=2)
        return f"Error querying blog posts: {response.status_code}"
    
    elif uri == "rdf://ontologies":
        return """# Available Ontologies

## Blog Post Ontology (ex:)
- ex:BlogPost - A blog post published on the web
- ex:Author - A person who writes blog posts  
- ex:hasTitle - The title of a blog post
- ex:hasContent - The content of a blog post
- ex:hasAuthor - The author of a blog post
- ex:publishedAt - When the blog post was published
- ex:isPublished - Whether the blog post is published

## Base Classes
- ex:Agent - An agent that can perform actions
- ex:Statement - A statement or claim
- ex:Place - A location or place
"""
    
    return "Resource not found"

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="sparql_query",
            description="Execute a SPARQL query against the RDF knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SPARQL query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="add_triple",
            description="Add a triple to the RDF knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject URI"},
                    "predicate": {"type": "string", "description": "Predicate URI"},
                    "object": {"type": "string", "description": "Object value"},
                    "object_type": {
                        "type": "string",
                        "enum": ["uri", "literal"],
                        "default": "literal",
                        "description": "Type of object"
                    }
                },
                "required": ["subject", "predicate", "object"]
            }
        ),
        Tool(
            name="create_blog_post",
            description="Create a new blog post in the knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Blog post title"},
                    "content": {"type": "string", "description": "Blog post content"},
                    "author_uri": {"type": "string", "description": "Author URI (e.g., http://example.org/alice)"},
                    "slug": {"type": "string", "description": "URL slug for the post"}
                },
                "required": ["title", "content", "author_uri"]
            }
        ),
        Tool(
            name="trigger_reasoning",
            description="Trigger OWL reasoning to compute inferences",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="trigger_validation",
            description="Trigger SHACL validation to check constraints",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "sparql_query":
        query = arguments.get("query")
        response = requests.post(f"{STORAGE_URL}/sparql", json={"query": query})
        
        if response.status_code == 200:
            results = response.json()
            
            if "results" in results:
                bindings = results["results"].get("bindings", [])
                if bindings:
                    result_text = "Results:\n"
                    for binding in bindings:
                        result_text += "  " + " | ".join([
                            f"{k}: {v.get('value', '')}" for k, v in binding.items()
                        ]) + "\n"
                    return [TextContent(type="text", text=result_text)]
                return [TextContent(type="text", text="No results found")]
            
            return [TextContent(type="text", text=str(results))]
        
        return [TextContent(type="text", text=f"Query failed: {response.status_code}")]
    
    elif name == "add_triple":
        response = requests.post(f"{STORAGE_URL}/triples", json=arguments)
        if response.status_code == 200:
            data = response.json()
            return [TextContent(type="text", text=f"✓ Triple added: {data.get('message')}")]
        return [TextContent(type="text", text=f"Failed to add triple: {response.status_code}")]
    
    elif name == "create_blog_post":
        title = arguments.get("title")
        content = arguments.get("content")
        author_uri = arguments.get("author_uri")
        slug = arguments.get("slug", title.lower().replace(" ", "-"))
        
        post_uri = f"http://example.org/posts/{slug}"
        now = datetime.now().isoformat()
        
        triples = [
            {
                "subject": post_uri,
                "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "object": "http://example.org/BlogPost",
                "object_type": "uri"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/hasTitle",
                "object": title,
                "object_type": "literal"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/hasContent",
                "object": content,
                "object_type": "literal"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/hasAuthor",
                "object": author_uri,
                "object_type": "uri"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/publishedAt",
                "object": now,
                "object_type": "literal"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/hasSlug",
                "object": slug,
                "object_type": "literal"
            },
            {
                "subject": post_uri,
                "predicate": "http://example.org/isPublished",
                "object": "true",
                "object_type": "literal"
            }
        ]
        
        for triple in triples:
            requests.post(f"{STORAGE_URL}/triples", json=triple)
        
        return [TextContent(
            type="text",
            text=f"✓ Blog post created: {title}\n  URI: {post_uri}\n  Author: {author_uri}\n  Published: {now}"
        )]
    
    elif name == "trigger_reasoning":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("reason.requested", "default", "{}"))
        conn.commit()
        cur.close()
        conn.close()
        
        return [TextContent(type="text", text="✓ Reasoning triggered. Check the inference graph for results.")]
    
    elif name == "trigger_validation":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("validate.requested", "default", "{}"))
        conn.commit()
        cur.close()
        conn.close()
        
        return [TextContent(type="text", text="✓ Validation triggered. Check the validation graph for results.")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
