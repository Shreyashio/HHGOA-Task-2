import React, { useState } from 'react';

const SAMPLE_QUERIES = [
  'What is photosynthesis and how does it work?',
  'Who is the Prime Minister of India?',
  'What are the main symptoms of diabetes?',
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
    <div className="w-full mt-3 max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask anything in English, Marathi, or Hindi..."
          disabled={isProcessing}
          className="w-full bg-[#161B22]/80 border border-white/[0.08] focus:border-[#FF6B35]/50 rounded-xl py-2.5 pl-3.5 pr-20 text-xs sm:text-sm text-[#F5F0E6] placeholder-[#8A8F94]/70 shadow-inner focus:outline-none transition-colors"
        />

        <div className="absolute right-1.5 flex items-center gap-1">
          {text && !isProcessing && (
            <button
              type="button"
              onClick={() => setText('')}
              className="p-1 text-[#8A8F94] hover:text-[#F5F0E6] transition-colors"
              title="Clear"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          <button
            type="submit"
            disabled={!text.trim() || isProcessing}
            className="px-3 py-1.5 rounded-lg bg-[#FF6B35] hover:bg-[#FF8254] disabled:opacity-30 disabled:cursor-not-allowed text-[#0B0E11] font-semibold text-xs transition-all"
          >
            Ask
          </button>
        </div>
      </form>

      {/* Subtle sample prompts */}
      <div className="mt-2 flex flex-wrap items-center justify-center gap-1.5 text-xs text-[#8A8F94]">
        {SAMPLE_QUERIES.map((sample, idx) => (
          <button
            key={idx}
            type="button"
            disabled={isProcessing}
            onClick={() => handleSelectSample(sample)}
            className="px-2 py-0.5 rounded-md bg-white/[0.03] hover:bg-white/[0.08] text-[#8A8F94] hover:text-[#F5F0E6] text-[11px] transition-colors truncate max-w-[200px] sm:max-w-none"
          >
            {sample}
          </button>
        ))}
      </div>
    </div>
  );
}
