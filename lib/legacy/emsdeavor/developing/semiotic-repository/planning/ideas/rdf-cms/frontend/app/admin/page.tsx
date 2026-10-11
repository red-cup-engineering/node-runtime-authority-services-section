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

export default function AdminPage() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    author: 'alice',
    content: '',
  });

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      const query = `
        PREFIX ex: <http://example.org/>
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

  const handleCreatePost = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const postUri = `http://example.org/posts/${formData.slug}`;
    const authorUri = `http://example.org/${formData.author}`;
    const now = new Date().toISOString();

    try {
      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: authorUri,
          predicate: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
          object: 'http://example.org/Author',
          object_type: 'uri',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
          object: 'http://example.org/BlogPost',
          object_type: 'uri',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://example.org/hasTitle',
          object: formData.title,
          object_type: 'literal',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://example.org/hasContent',
          object: formData.content,
          object_type: 'literal',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://example.org/hasAuthor',
          object: authorUri,
          object_type: 'uri',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://example.org/hasSlug',
          object: formData.slug,
          object_type: 'literal',
        }),
      });

      await fetch('/api/triples', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: postUri,
          predicate: 'http://example.org/publishedAt',
          object: now,
          object_type: 'literal',
        }),
      });

      setFormData({ title: '', slug: '', author: 'alice', content: '' });
      setShowCreateForm(false);
      await fetchPosts();
    } catch (error) {
      console.error('Error creating post:', error);
      alert('Error creating post. Please try again.');
    }
  };

  const handleDelete = async (uri: string) => {
    if (!confirm('Are you sure you want to delete this post?')) return;

    try {
      const query = `
        PREFIX ex: <http://example.org/>
        SELECT ?p ?o
        WHERE {
          <${uri}> ?p ?o
        }
      `;

      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (response.ok) {
        const data = await response.json();
        for (const binding of data.results.bindings) {
          const objectType = binding.o.type === 'uri' ? 'uri' : 'literal';
          await fetch('/api/triples', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              subject: uri,
              predicate: binding.p.value,
              object: binding.o.value,
              object_type: objectType,
            }),
          });
        }
        await fetchPosts();
      }
    } catch (error) {
      console.error('Error deleting post:', error);
      alert('Error deleting post. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Blog Admin</h1>
            <p className="text-sm text-gray-600">Manage your semantic web blog posts</p>
          </div>
          <Link 
            href="/" 
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md"
          >
            ← Back to Blog
          </Link>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">Your Posts</h2>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
          >
            {showCreateForm ? 'Cancel' : '+ New Post'}
          </button>
        </div>

        {showCreateForm && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Post</h3>
            <form onSubmit={handleCreatePost} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter post title..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Slug (URL-friendly)
                </label>
                <input
                  type="text"
                  required
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="my-post-slug"
                />
                <p className="text-xs text-gray-500 mt-1">Will be used in URL: /posts/{formData.slug || 'my-post-slug'}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Author
                </label>
                <input
                  type="text"
                  required
                  value={formData.author}
                  onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="author-name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Content
                </label>
                <textarea
                  required
                  rows={8}
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Write your blog post content here..."
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
                >
                  Publish Post
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-4 text-gray-600">Loading posts...</p>
          </div>
        ) : posts.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <p className="text-gray-600 mb-4">No posts yet. Create your first one!</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Author
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Published
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {posts.map((post) => (
                  <tr key={post.uri} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{post.title}</div>
                      <div className="text-xs text-gray-500">/posts/{post.slug}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {post.author}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {post.publishedAt ? new Date(post.publishedAt).toLocaleDateString() : 'Draft'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link
                        href={`/posts/${post.slug}`}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => handleDelete(post.uri)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
