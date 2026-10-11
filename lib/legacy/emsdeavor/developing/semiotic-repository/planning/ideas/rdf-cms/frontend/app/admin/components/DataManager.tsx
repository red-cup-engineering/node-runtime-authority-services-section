'use client';

import { useState } from 'react';

export default function DataManager() {
  const [subject, setSubject] = useState('http://example.org/kb/Statement1');
  const [predicate, setPredicate] = useState('http://www.w3.org/1999/02/22-rdf-syntax-ns#type');
  const [object, setObject] = useState('http://example.org/kb/Statement');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const addTriple = async () => {
    setLoading(true);
    setMessage(null);

    const updateQuery = `INSERT DATA { <${subject}> <${predicate}> <${object}> }`;

    try {
      const response = await fetch('/api/sparql/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ update: updateQuery }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: 'Triple added successfully!' });
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to add triple' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }

    setLoading(false);
  };

  const deleteTriple = async () => {
    setLoading(true);
    setMessage(null);

    const updateQuery = `DELETE DATA { <${subject}> <${predicate}> <${object}> }`;

    try {
      const response = await fetch('/api/sparql/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ update: updateQuery }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: 'Triple deleted successfully!' });
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to delete triple' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }

    setLoading(false);
  };

  const exampleTriples = [
    {
      name: 'New Statement',
      subject: 'http://example.org/kb/Statement1',
      predicate: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
      object: 'http://example.org/kb/Statement'
    },
    {
      name: 'With Author',
      subject: 'http://example.org/kb/Statement1',
      predicate: 'http://example.org/kb/hasAuthor',
      object: 'http://example.org/kb/Agent1'
    },
    {
      name: 'New Agent',
      subject: 'http://example.org/kb/Agent1',
      predicate: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
      object: 'http://example.org/kb/Agent'
    }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Add or Delete Triples</h3>
        
        <div className="flex gap-2 mb-4">
          {exampleTriples.map((example) => (
            <button
              key={example.name}
              onClick={() => {
                setSubject(example.subject);
                setPredicate(example.predicate);
                setObject(example.object);
              }}
              className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
            >
              {example.name}
            </button>
          ))}
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject (IRI)</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md font-mono text-sm text-gray-900"
              placeholder="http://example.org/kb/Subject1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Predicate (IRI)</label>
            <input
              type="text"
              value={predicate}
              onChange={(e) => setPredicate(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md font-mono text-sm text-gray-900"
              placeholder="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Object (IRI)</label>
            <input
              type="text"
              value={object}
              onChange={(e) => setObject(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md font-mono text-sm text-gray-900"
              placeholder="http://example.org/kb/Object1"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={addTriple}
              disabled={loading}
              className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400 transition-colors"
            >
              {loading ? 'Processing...' : 'Add Triple'}
            </button>

            <button
              onClick={deleteTriple}
              disabled={loading}
              className="bg-red-600 text-white px-6 py-2 rounded-md hover:bg-red-700 disabled:bg-gray-400 transition-colors"
            >
              {loading ? 'Processing...' : 'Delete Triple'}
            </button>
          </div>
        </div>
      </div>

      {message && (
        <div className={`rounded-lg p-4 ${
          message.type === 'success' 
            ? 'bg-green-50 border border-green-200' 
            : 'bg-red-50 border border-red-200'
        }`}>
          <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
            {message.text}
          </p>
        </div>
      )}
    </div>
  );
}
