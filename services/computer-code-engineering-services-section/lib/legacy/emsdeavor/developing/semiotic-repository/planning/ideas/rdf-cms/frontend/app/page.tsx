'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface BlogPost {
  uri: string;
  title: string;
  author: string;
  content: string;
  publishedAt: string;
  slug: string;
}

export default function Home() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      const query = `
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?post ?title ?author ?content ?published ?slug
        WHERE {
          ?post a ex:BlogPost .
          OPTIONAL { ?post ex:hasTitle ?title }
          OPTIONAL { ?post ex:hasAuthor ?authorUri . 
                     BIND(REPLACE(STR(?authorUri), ".*/(.*)", "$1") AS ?author) }
          OPTIONAL { ?post ex:hasContent ?content }
          OPTIONAL { ?post ex:publishedAt ?published }
          OPTIONAL { ?post ex:hasSlug ?slug }
        }
        ORDER BY DESC(?published)
      `;

      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (response.ok) {
        const data = await response.json();
        const blogPosts: BlogPost[] = data.results.bindings.map((b: any) => ({
          uri: b.post?.value || '',
          title: b.title?.value || 'Untitled',
          author: b.author?.value || 'Anonymous',
          content: b.content?.value || '',
          publishedAt: b.published?.value || '',
          slug: b.slug?.value || b.post?.value.split('/').pop() || '',
        }));
        setPosts(blogPosts);
      }
    } catch (error) {
      console.error('Error fetching posts:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Graph Blog</h1>
          <Link 
            href="/admin" 
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md"
          >
            Admin
          </Link>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h2 className="text-4xl font-bold text-gray-900 mb-2">Blog Posts</h2>
          <p className="text-gray-600">Powered by RDF semantic knowledge graph with OWL reasoning</p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-4 text-gray-600">Loading posts...</p>
          </div>
        ) : posts.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
            <p className="text-gray-600 mb-4">No blog posts yet.</p>
            <Link 
              href="/admin" 
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Create Your First Post
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {posts.map((post) => (
              <article 
                key={post.uri} 
                className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow p-6"
              >
                <Link href={`/posts/${post.slug}`}>
                  <h3 className="text-2xl font-bold text-gray-900 mb-2 hover:text-blue-600">
                    {post.title}
                  </h3>
                </Link>
                
                <div className="flex items-center text-sm text-gray-600 mb-4">
                  <span className="font-medium text-gray-900">{post.author}</span>
                  {post.publishedAt && (
                    <>
                      <span className="mx-2">•</span>
                      <time>{new Date(post.publishedAt).toLocaleDateString()}</time>
                    </>
                  )}
                </div>

                <p className="text-gray-700 line-clamp-3 mb-4">
                  {post.content || 'No content available.'}
                </p>

                <Link 
                  href={`/posts/${post.slug}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Read more →
                </Link>
              </article>
            ))}
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600 text-sm">
            Semantic Web Knowledge Graph • RDF + OWL + SHACL + MCP
          </p>
        </div>
      </footer>
    </div>
  );
}
