'use client';

import { useState } from 'react';

export default function SystemControls() {
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const triggerReasoning = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/trigger/reasoning', {
        method: 'POST',
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Reasoning triggered successfully!' });
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to trigger reasoning' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }

    setLoading(false);
  };

  const triggerValidation = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/trigger/validation', {
        method: 'POST',
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Validation triggered successfully!' });
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to trigger validation' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }

    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-4">System Operations</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <h4 className="font-semibold text-gray-900 mb-2">OWL Reasoning</h4>
            <p className="text-sm text-gray-600 mb-4">
              Compute inferences from your ontology and data using OWL reasoning. 
              Results are written to the inference graph.
            </p>
            <button
              onClick={triggerReasoning}
              disabled={loading}
              className="bg-purple-600 text-white px-6 py-2 rounded-md hover:bg-purple-700 disabled:bg-gray-400 transition-colors w-full"
            >
              {loading ? 'Processing...' : 'Run Reasoner'}
            </button>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <h4 className="font-semibold text-gray-900 mb-2">SHACL Validation</h4>
            <p className="text-sm text-gray-600 mb-4">
              Validate your data against SHACL constraint shapes. 
              Validation reports are written to the validation graph.
            </p>
            <button
              onClick={triggerValidation}
              disabled={loading}
              className="bg-orange-600 text-white px-6 py-2 rounded-md hover:bg-orange-700 disabled:bg-gray-400 transition-colors w-full"
            >
              {loading ? 'Processing...' : 'Run Validator'}
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

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-semibold text-blue-900 mb-2">How it works</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Reasoner publishes events to NATS message bus (reason.requested)</li>
          <li>• Validator publishes events to NATS (validate.requested)</li>
          <li>• Services process in background and update respective graphs</li>
          <li>• Use Graph Explorer to view inference and validation results</li>
        </ul>
      </div>
    </div>
  );
}
