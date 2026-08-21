import React from 'react';

const STAGES = [
  {
    id: 'voice',
    title: 'Voice Input',
    sub: 'Mic Audio',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
    ),
    latencyKey: 'input_validation_ms',
  },
  {
    id: 'stt',
    title: 'STT Audio',
    sub: 'Sarvam AI',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    latencyKey: 'stt_ms',
  },
  {
    id: 'retrieve',
    title: 'Vector Search',
    sub: 'ChromaDB Top-10',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
    latencyKey: 'retrieval_ms',
  },
  {
    id: 'rerank',
    title: 'BM25 Rerank',
    sub: 'Reciprocal Rank Fusion',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
      </svg>
    ),
    latencyKey: 'reranking_ms',
  },
  {
    id: 'generate',
    title: 'LLM Gen',
    sub: 'Groq / Llama 3',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    latencyKey: 'generation_ms',
  },
  {
    id: 'answer',
    title: 'Verified Answer',
    sub: 'Grounded Output',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    latencyKey: 'total_ms',
  },
];

export default function PipelineStrip({ currentStage, latencyData, isProcessing }) {
  const activeIndex = STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="w-full mt-6 mb-2">
      <div className="rounded-xl p-3 border border-hhg-border bg-hhg-card/60 backdrop-blur-sm text-xs">
        {/* Subtle section label */}
        <div className="flex items-center justify-between mb-2 px-1 text-[11px] font-mono text-hhg-sand-muted">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-hhg-teal" />
            <span className="uppercase tracking-wider">Pipeline Architecture</span>
          </div>

          <div className="flex items-center gap-1 text-[10px]">
            <span>Target: <strong className="text-emerald-400">&lt;200ms</strong></span>
          </div>
        </div>

        {/* Compact Horizontal Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5 sm:gap-2">
          {STAGES.map((stage, idx) => {
            const isActive = currentStage === stage.id;
            const isCompleted = latencyData && !isProcessing && activeIndex === -1;
            const isPast = activeIndex > idx;
            const stageMs = latencyData?.[stage.latencyKey];

            return (
              <div
                key={stage.id}
                className={`relative rounded-lg p-2 flex flex-col justify-between transition-all duration-200 border ${
                  isActive
                    ? 'bg-hhg-coral/20 border-hhg-coral shadow-[0_0_12px_rgba(255,107,53,0.3)] scale-[1.02]'
                    : isCompleted || isPast
                    ? 'bg-hhg-surface/80 border-hhg-border text-hhg-sand'
                    : 'bg-hhg-card/40 border-hhg-border/50 opacity-60 text-hhg-sand-muted'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div
                    className={`p-1 rounded ${
                      isActive
                        ? 'bg-hhg-coral text-[#0B0E11]'
                        : isCompleted || isPast
                        ? 'bg-hhg-surface text-hhg-teal'
                        : 'bg-hhg-card text-hhg-sand-dim'
                    }`}
                  >
                    {stage.icon}
                  </div>

                  <span className="text-[9px] font-mono text-hhg-sand-dim">
                    0{idx + 1}
                  </span>
                </div>

                <div>
                  <h4 className="font-semibold text-[11px] text-hhg-sand leading-tight flex items-center gap-1">
                    {stage.title}
                    {isActive && (
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-hhg-coral animate-ping" />
                    )}
                  </h4>
                  <p className="text-[9px] text-hhg-sand-dim truncate mt-0.5">
                    {stage.sub}
                  </p>
                </div>

                {typeof stageMs === 'number' && stageMs > 0 && (
                  <div className="mt-1 pt-1 border-t border-hhg-border/40 flex items-center justify-between text-[9px] font-mono">
                    <span className="text-hhg-sand-dim">Time</span>
                    <span className="text-hhg-teal font-semibold">
                      {stageMs.toFixed(0)}ms
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
