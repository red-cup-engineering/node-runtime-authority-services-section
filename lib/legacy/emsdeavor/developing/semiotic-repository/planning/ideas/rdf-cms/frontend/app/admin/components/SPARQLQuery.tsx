'use client';

import { useState } from 'react';

export default function SPARQLQuery() {
  const [query, setQuery] = useState('SELECT * WHERE { ?s ?p ?o } LIMIT 10');
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const executeSPARQL = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        setError(data.error || `Query failed with status ${response.status}`);
      } else if (data.error) {
        setError(data.error);
      } else {
        setResults(data);
      }
    } catch (err) {
      setError(`Network error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
    
    setLoading(false);
  };

  const exampleQueries = [
    {
      name: 'All Triples',
      query: 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
    },
    {
      name: 'All Classes',
      query: 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nPREFIX owl: <http://www.w3.org/2002/07/owl#>\nSELECT DISTINCT ?class WHERE { ?class rdf:type owl:Class }'
    },
    {
      name: 'All Statements',
      query: 'PREFIX ex: <http://example.org/kb/>\nSELECT * WHERE { ?s a ex:Statement . ?s ?p ?o }'
    },
    {
      name: 'SHACL Shapes',
      query: 'PREFIX sh: <http://www.w3.org/ns/shacl#>\nSELECT * WHERE { ?shape a sh:NodeShape . ?shape ?p ?o }'
    }
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800">SPARQL Query</h3>
          <div className="flex gap-2">
            {exampleQueries.map((example) => (
              <button
                key={example.name}
                onClick={() => setQuery(example.query)}
                className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
              >
                {example.name}
              </button>
            ))}
          </div>
        </div>
        
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full h-40 p-3 border border-gray-300 rounded-md font-mono text-sm text-gray-900"
          placeholder="Enter SPARQL query..."
        />
        
        <button
          onClick={executeSPARQL}
          disabled={loading}
          className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Executing...' : 'Execute Query'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-2 text-red-800">Error</h3>
          <p className="text-red-600 font-mono text-sm">{error}</p>
        </div>
      )}

      {results && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-800">Results</h3>
          <div className="mb-4">
            <span className="text-sm text-gray-600">
              {results.results?.bindings?.length || 0} results
            </span>
          </div>
          
          {results.results?.bindings?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(results.results.bindings[0]).map((key) => (
                      <th key={key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {results.results.bindings.map((binding: any, idx: number) => (
                    <tr key={idx}>
                      {Object.keys(binding).map((key) => (
                        <td key={key} className="px-4 py-3 text-sm text-gray-900 font-mono">
                          {binding[key].value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500">No results</p>
          )}
        </div>
      )}
    </div>
  );
}
