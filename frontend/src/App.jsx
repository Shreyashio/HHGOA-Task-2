import './index.css'

/**
 * App.jsx — Placeholder UI (Step 1)
 *
 * This will be replaced in Step 4/5 with the full voice-RAG interface:
 *   - Mic button → MediaRecorder → audio blob → POST /api/v1/query/voice
 *   - Text input fallback → POST /api/v1/query/text
 *   - Answer card with retrieved chunk citations
 *   - Latency breakdown panel (P50/P70/P100)
 *   - Chunking strategy selector
 */
function App() {
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 mb-4 px-4 py-1.5 rounded-full glass text-brand-400 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse-slow" />
          HH Goa 2026 · Task 2
        </div>
        <h1 className="text-5xl font-bold text-white mb-3 tracking-tight">
          Voice{' '}
          <span className="bg-gradient-to-r from-brand-400 to-purple-400 bg-clip-text text-transparent">
            RAG
          </span>
        </h1>
        <p className="text-gray-400 text-lg max-w-md mx-auto">
          Speak a question. Get a grounded answer from MSMARCO-XI — under 200ms.
        </p>
      </div>

      {/* Placeholder mic button */}
      <div className="relative">
        <div className="w-28 h-28 rounded-full glass flex items-center justify-center
                        cursor-not-allowed opacity-60 transition-all duration-300">
          <svg className="w-10 h-10 text-brand-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"/>
          </svg>
        </div>
      </div>

      <p className="mt-6 text-gray-500 text-sm">
        Backend not connected — start with{' '}
        <code className="text-brand-400 bg-gray-900 px-1.5 py-0.5 rounded text-xs">
          uvicorn backend.main:app --reload
        </code>
      </p>

      {/* Status grid */}
      <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-2xl">
        {[
          { label: 'STT', status: 'Sarvam AI', color: 'text-yellow-400' },
          { label: 'Vector DB', status: 'ChromaDB', color: 'text-green-400' },
          { label: 'LLM', status: 'Groq', color: 'text-purple-400' },
          { label: 'Pipeline', status: '< 200ms target', color: 'text-brand-400' },
        ].map(({ label, status, color }) => (
          <div key={label} className="glass rounded-xl p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">{label}</p>
            <p className={`font-semibold text-sm ${color}`}>{status}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App
