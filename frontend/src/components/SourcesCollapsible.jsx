import React, { useState } from 'react';

export default function SourcesCollapsible({ sources }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="w-full paithani-card border-paithani-border/70 my-3 overflow-hidden">
      {/* Accordion Toggle Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 bg-paithani-surface/60 hover:bg-paithani-surface transition-colors flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="p-1 rounded-md bg-paithani-maroon/50 text-paithani-gold-light">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </span>
          <div>
            <h4 className="font-marathi font-bold text-sm text-paithani-ivory leading-tight">
              वापरलेले संदर्भ स्रोत (Source Chunks Used)
            </h4>
            <p className="text-[11px] text-paithani-ivory-dim">
              {sources.length} MSMARCO-XI retrieved passages verified for grounding
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-full bg-paithani-card border border-paithani-border text-[11px] font-mono text-paithani-gold-light">
            {sources.length} chunks
          </span>
          <svg
            className={`w-4 h-4 text-paithani-ivory-muted transition-transform duration-200 ${
              isOpen ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Accordion Body */}
      {isOpen && (
        <div className="p-4 space-y-3 border-t border-paithani-border/50 bg-[#120D0C]/60">
          {sources.map((src, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-paithani-card/90 border border-paithani-border/80 hover:border-paithani-gold/30 transition-all text-xs"
            >
              {/* Chunk metadata bar */}
              <div className="flex flex-wrap items-center justify-between gap-1.5 pb-2 mb-2 border-b border-paithani-border/40 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-paithani-gold-light bg-paithani-surface px-1.5 py-0.5 rounded">
                    #{src.source_index !== undefined ? src.source_index + 1 : idx + 1}
                  </span>
                  <span className="font-mono text-paithani-ivory font-semibold truncate max-w-[160px] sm:max-w-none">
                    {src.doc_id || `DOC_${idx + 1}`}
                  </span>
                  {src.chunk_id && (
                    <span className="font-mono text-paithani-ivory-dim">
                      ({src.chunk_id})
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {src.lang && (
                    <span className="px-2 py-0.5 rounded bg-paithani-surface text-paithani-ivory-muted font-medium uppercase text-[10px]">
                      {src.lang}
                    </span>
                  )}
                  {src.score !== undefined && (
                    <span className="px-2 py-0.5 rounded bg-paithani-maroon/40 border border-paithani-maroon text-paithani-gold-light font-mono font-medium text-[10px]">
                      Score: {Number(src.score).toFixed(3)}
                    </span>
                  )}
                </div>
              </div>

              {/* Chunk Snippet */}
              <p className="font-marathi text-paithani-ivory text-xs sm:text-sm leading-relaxed whitespace-pre-line pl-1 italic text-paithani-ivory-muted">
                &ldquo;{src.snippet}&rdquo;
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
