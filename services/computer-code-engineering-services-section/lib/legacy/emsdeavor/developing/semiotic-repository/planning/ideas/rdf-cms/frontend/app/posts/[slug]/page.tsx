'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

interface BlogPost {
  uri: string;
  title: string;
  author: string;
  authorUri: string;
  content: string;
  publishedAt: string;
  slug: string;
  isPublished: boolean;
}

export default function BlogPostPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [post, setPost] = useState<BlogPost | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (slug) {
      fetchPost();
    }
  }, [slug]);

  const fetchPost = async () => {
    try {
      const query = `
        PREFIX ex: <http://example.org/>
        
        SELECT ?post ?title ?authorUri ?content ?published ?isPublished
        WHERE {
          ?post ex:hasSlug "${slug}" .
          ?post a ex:BlogPost .
          OPTIONAL { ?post ex:hasTitle ?title }
          OPTIONAL { ?post ex:hasAuthor ?authorUri }
          OPTIONAL { ?post ex:hasContent ?content }
          OPTIONAL { ?post ex:publishedAt ?published }
          OPTIONAL { ?post ex:isPublished ?isPublished }
        }
      `;

      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.results.bindings.length > 0) {
          const b = data.results.bindings[0];
          const authorName = b.authorUri?.value.split('/').pop() || 'Anonymous';
          setPost({
            uri: b.post?.value || '',
            title: b.title?.value || 'Untitled',
            author: authorName,
            authorUri: b.authorUri?.value || '',
            content: b.content?.value || '',
            publishedAt: b.published?.value || '',
            slug: slug,
            isPublished: b.isPublished?.value === 'true',
          });
        }
      }
    } catch (error) {
      console.error('Error fetching post:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading post...</p>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <Link href="/" className="text-blue-600 hover:text-blue-800 font-medium">
              ← Back to Blog
            </Link>
          </div>
        </nav>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Post Not Found</h1>
          <p className="text-gray-600 mb-8">The blog post you're looking for doesn't exist.</p>
          <Link href="/" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Go to Homepage
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <Link href="/" className="text-blue-600 hover:text-blue-800 font-medium">
            ← Back to Blog
          </Link>
          <Link 
            href="/admin" 
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md"
          >
            Admin
          </Link>
        </div>
      </nav>

      <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <header className="mb-8">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">{post.title}</h1>
          <div className="flex items-center text-gray-600">
            <span className="font-medium text-gray-900">{post.author}</span>
            {post.publishedAt && (
              <>
                <span className="mx-2">•</span>
                <time>{new Date(post.publishedAt).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}</time>
              </>
            )}
            {!post.isPublished && (
              <>
                <span className="mx-2">•</span>
                <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded">
                  Draft
                </span>
              </>
            )}
          </div>
        </header>

        <div className="prose prose-lg max-w-none">
          <div className="bg-white rounded-lg shadow-sm p-8">
            {post.content.split('\n\n').map((paragraph, index) => (
              <p key={index} className="mb-4 text-gray-700 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        </div>

        <footer className="mt-12 pt-8 border-t border-gray-200">
          <div className="bg-blue-50 rounded-lg p-6">
            <h3 className="text-sm font-medium text-blue-900 mb-2">Semantic Web Metadata</h3>
            <dl className="grid grid-cols-1 gap-2 text-sm">
              <div>
                <dt className="inline font-medium text-blue-800">URI:</dt>
                <dd className="inline ml-2 text-blue-600 font-mono text-xs">{post.uri}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-blue-800">Author URI:</dt>
                <dd className="inline ml-2 text-blue-600 font-mono text-xs">{post.authorUri}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-blue-800">Type:</dt>
                <dd className="inline ml-2 text-blue-600">ex:BlogPost</dd>
              </div>
            </dl>
          </div>
        </footer>
      </article>
    </div>
  );
}
