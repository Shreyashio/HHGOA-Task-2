import React from 'react';

const LANGUAGE_OPTIONS = [
  { code: 'en-IN', label: 'English' },
  { code: 'mr-IN', label: 'मराठी' },
  { code: 'hi-IN', label: 'हिंदी' },
];

export default function Header({ selectedLang, setSelectedLang }) {
  return (
    <header className="w-full border-b border-white/[0.06] bg-[#0B0E11]/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Clean Serif Wordmark Anchor */}
        <div className="flex items-center gap-2.5">
          <h1 className="font-marathi text-2xl font-bold text-[#F5F0E6] tracking-wide select-none">
            मातृभाषा
          </h1>
        </div>

        {/* The single primary interactive header control: Language Selector */}
        <div className="flex items-center gap-2">
          <div className="relative flex items-center">
            <select
              value={selectedLang || 'en-IN'}
              onChange={(e) => setSelectedLang(e.target.value)}
              className="appearance-none bg-[#161B22] hover:bg-[#1C222B] text-xs text-[#F5F0E6] font-medium py-1.5 pl-3 pr-8 rounded-lg border border-white/[0.08] hover:border-white/[0.16] focus:outline-none focus:border-[#FF6B35]/60 transition-colors cursor-pointer"
              title="Select spoken / query language"
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code} className="bg-[#12161B] text-[#F5F0E6]">
                  {opt.label}
                </option>
              ))}
            </select>
            <svg
              className="w-3.5 h-3.5 text-[#8A8F94] pointer-events-none absolute right-2.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
    </header>
  );
}
