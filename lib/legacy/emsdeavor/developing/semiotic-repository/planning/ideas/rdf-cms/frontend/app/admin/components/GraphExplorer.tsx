'use client';

import { useState } from 'react';

export default function GraphExplorer() {
  const [selectedGraph, setSelectedGraph] = useState('default');
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const graphs = [
    { id: 'default', name: 'Default Graph', description: 'Main ontology and data' },
    { id: 'http://example.org/kb/inferred/', name: 'Inference Graph', description: 'OWL-derived triples' },
    { id: 'http://example.org/kb/validation/', name: 'Validation Graph', description: 'SHACL validation reports' }
  ];

  const exploreGraph = async () => {
    setLoading(true);
    
    const query = selectedGraph === 'default'
      ? 'SELECT * WHERE { ?s ?p ?o } LIMIT 50'
      : `SELECT * WHERE { GRAPH <${selectedGraph}> { ?s ?p ?o } } LIMIT 50`;

    try {
      const response = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Failed to explore graph:', err);
    }
    
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Graph Explorer</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {graphs.map((graph) => (
            <button
              key={graph.id}
              onClick={() => setSelectedGraph(graph.id)}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                selectedGraph === graph.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <h4 className="font-semibold text-gray-900 mb-1">{graph.name}</h4>
              <p className="text-sm text-gray-600">{graph.description}</p>
            </button>
          ))}
        </div>

        <button
          onClick={exploreGraph}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Loading...' : `Explore ${graphs.find(g => g.id === selectedGraph)?.name}`}
        </button>
      </div>

      {results && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-800">
            {graphs.find(g => g.id === selectedGraph)?.name} Contents
          </h3>
          <div className="mb-4">
            <span className="text-sm text-gray-600">
              {results.results?.bindings?.length || 0} triples (limit 50)
            </span>
          </div>
          
          {results.results?.bindings?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subject</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Predicate</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Object</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {results.results.bindings.map((binding: any, idx: number) => (
                    <tr key={idx}>
                      <td className="px-4 py-3 text-sm text-gray-900 font-mono break-all max-w-xs">{binding.s?.value}</td>
                      <td className="px-4 py-3 text-sm text-blue-600 font-mono break-all max-w-xs">{binding.p?.value}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 font-mono break-all max-w-xs">{binding.o?.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500">Graph is empty</p>
          )}
        </div>
      )}
    </div>
  );
}
