import React, { useState } from 'react';

const SAMPLE_QUERIES = [
  { label: 'Photosynthesis', query: 'what is photosynthesis and how does it work?' },
  { label: 'Prime Minister of India', query: 'who is the prime minister of india' },
  { label: 'First President of India', query: 'who was the first president of India' },
  { label: 'Diabetes Symptoms', query: 'what are the main symptoms of diabetes' },
];

export default function TextFallback({ onSendText, isProcessing }) {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (trimmed && !isProcessing) {
      onSendText(trimmed);
    }
  };

  const handleSelectSample = (sample) => {
    setText(sample);
    if (!isProcessing) {
      onSendText(sample);
    }
  };

  return (
    <div className="w-full mt-2">
      <form onSubmit={handleSubmit} className="relative flex items-center">
        {/* Terminal Search input with HH Goa border */}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Or type your question in English, Marathi, or Hindi..."
          disabled={isProcessing}
          className="w-full bg-hhg-surface border border-hhg-border focus:border-hhg-coral rounded-xl py-3 pl-4 pr-24 text-sm text-hhg-sand placeholder-hhg-sand-muted/70 shadow-inner focus:outline-none focus:ring-1 focus:ring-hhg-coral transition-all duration-200"
        />

        {/* Clear & Send action button */}
        <div className="absolute right-2 flex items-center gap-1.5">
          {text && !isProcessing && (
            <button
              type="button"
              onClick={() => setText('')}
              className="p-1 rounded-lg text-hhg-sand-muted hover:text-hhg-sand hover:bg-hhg-cardHover transition-colors"
              title="Clear text"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          <button
            type="submit"
            disabled={!text.trim() || isProcessing}
            className="px-3.5 py-1.5 rounded-lg bg-hhg-coral hover:bg-hhg-coral-hover disabled:opacity-40 disabled:cursor-not-allowed text-[#0B0E11] font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-hhg-coral/20 transition-all duration-200 border border-hhg-coral-light/40"
          >
            <span>Search</span>
            <svg className="w-3.5 h-3.5 text-[#0B0E11]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </form>

      {/* Suggested Quick Prompt Pills */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-[11px] text-hhg-sand-muted flex items-center gap-1">
          <svg className="w-3 h-3 text-hhg-gold" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l2.4 7.2h7.6l-6.1 4.5 2.3 7.1-6.2-4.5-6.2 4.5 2.3-7.1-6.1-4.5h7.6z" />
          </svg>
          Samples:
        </span>
        {SAMPLE_QUERIES.map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={isProcessing}
            onClick={() => handleSelectSample(item.query)}
            className="px-2.5 py-1 rounded-lg bg-hhg-surface hover:bg-hhg-cardHover border border-hhg-border hover:border-hhg-coral/40 text-hhg-sand-muted hover:text-hhg-sand text-[11px] transition-all duration-150"
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
