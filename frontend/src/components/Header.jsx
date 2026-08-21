import React from 'react';

const LANGUAGE_OPTIONS = [
  { code: 'en-IN', label: 'English' },
  { code: 'mr-IN', label: 'मराठी' },
  { code: 'hi-IN', label: 'हिंदी' },
];

export default function Header({
  backendOnline,
  mockMode,
  setMockMode,
  strategy,
  setStrategy,
  selectedLang,
  setSelectedLang,
}) {
  return (
    <header className="w-full border-b border-hhg-border bg-hhg-bg/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 py-3 sm:py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Brand & Wordmark (Name is "मातृभाषा" only, no English transliteration/subtitle) */}
        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-start">
          <div className="flex items-center gap-3">
            {/* Terminal Emblem */}
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-hhg-coral to-hhg-coral-deep border border-hhg-coral/40 flex items-center justify-center shadow-lg shadow-hhg-coral/20 flex-shrink-0">
              <span className="font-marathi font-bold text-hhg-sand text-lg leading-none">
                मा
              </span>
            </div>
            
            <div className="flex items-center gap-2.5">
              <h1 className="font-marathi text-2xl font-bold text-hhg-sand tracking-wide leading-none">
                मातृभाषा
              </h1>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-hhg-surface border border-hhg-border text-hhg-teal uppercase tracking-wider">
                Voice-RAG
              </span>
            </div>
          </div>

          {/* Backend Status Indicator (Mobile) */}
          <div className="sm:hidden flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-hhg-card border border-hhg-border text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-hhg-teal animate-pulse' : 'bg-amber-500'
              }`}
            />
            <span className="text-hhg-sand-muted text-[11px] font-mono">
              {backendOnline ? 'API :8000' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Global Controls Strip */}
        <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-2.5 w-full sm:w-auto text-xs">
          {/* Language Selector (English default, options: English / मराठी / हिंदी) */}
          <div className="flex items-center gap-1.5 bg-hhg-surface border border-hhg-border px-2.5 py-1 rounded-lg">
            <svg className="w-3.5 h-3.5 text-hhg-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            <span className="text-hhg-sand-muted text-[11px] hidden md:inline">Language:</span>
            <select
              value={selectedLang || 'en'}
              onChange={(e) => setSelectedLang(e.target.value)}
              className="bg-transparent text-hhg-sand font-medium outline-none cursor-pointer text-xs"
              title="Select interaction language (English, Marathi, or Hindi)"
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code} className="bg-hhg-card text-hhg-sand">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Strategy Selector */}
          <div className="flex items-center gap-1.5 bg-hhg-surface border border-hhg-border px-2.5 py-1 rounded-lg">
            <span className="text-hhg-sand-dim text-[11px] hidden md:inline">Strategy:</span>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="bg-transparent text-hhg-teal font-medium outline-none cursor-pointer text-xs font-mono"
              title="Chunking strategy for vector retrieval"
            >
              <option value="sentence" className="bg-hhg-card text-hhg-sand">Sentence</option>
              <option value="fixed" className="bg-hhg-card text-hhg-sand">Fixed (256-tok)</option>
              <option value="metadata" className="bg-hhg-card text-hhg-sand">Metadata-rich</option>
            </select>
          </div>

          {/* Backend Status Badge (Desktop) */}
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-hhg-surface border border-hhg-border text-hhg-sand-muted">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline
                  ? 'bg-hhg-teal shadow-[0_0_8px_#1DBFA3]'
                  : 'bg-amber-500'
              }`}
            />
            <span className="font-mono text-[11px]">
              {backendOnline ? 'FastAPI :8000' : 'Offline'}
            </span>
          </div>

          {/* Mock Mode Toggle */}
          <button
            type="button"
            onClick={() => setMockMode(!mockMode)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-all duration-200 font-mono text-[11px] ${
              mockMode
                ? 'bg-hhg-gold/20 text-hhg-gold border-hhg-gold/50 shadow-[0_0_10px_rgba(255,179,71,0.2)]'
                : 'bg-hhg-surface text-hhg-sand-muted border-hhg-border hover:text-hhg-sand'
            }`}
            title="Toggle offline mock demo mode"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                mockMode ? 'bg-hhg-gold' : 'bg-hhg-sand-dim'
              }`}
            />
            {mockMode ? 'Mock ON' : 'Mock Mode'}
          </button>
        </div>
      </div>
    </header>
  );
}
