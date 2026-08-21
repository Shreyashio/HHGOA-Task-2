import React from 'react';

const STAGES = [
  { id: 'voice', label: 'Voice Input', latencyKey: 'input_validation_ms' },
  { id: 'stt', label: 'Sarvam STT', latencyKey: 'stt_ms' },
  { id: 'retrieve', label: 'Vector Search', latencyKey: 'retrieval_ms' },
  { id: 'rerank', label: 'BM25 RRF', latencyKey: 'reranking_ms' },
  { id: 'generate', label: 'Groq LLM', latencyKey: 'generation_ms' },
  { id: 'answer', label: 'Verified Output', latencyKey: 'total_ms' },
];

export default function PipelineStrip({ currentStage, latencyData, isProcessing }) {
  const activeIndex = STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="w-full mt-6 mb-3">
      <div className="py-2.5 px-3.5 rounded-xl bg-[#12161B]/60 border border-white/[0.05] text-xs">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {STAGES.map((stage, idx) => {
            const isActive = currentStage === stage.id;
            const isCompleted = latencyData && !isProcessing && activeIndex === -1;
            const stageMs = latencyData?.[stage.latencyKey];

            return (
              <div
                key={stage.id}
                className={`py-1.5 px-2 rounded-lg transition-colors flex flex-col justify-between ${
                  isActive
                    ? 'bg-[#FF6B35]/15 border border-[#FF6B35]/40 text-[#FF6B35]'
                    : isCompleted
                    ? 'text-[#F5F0E6]'
                    : 'text-[#8A8F94]/70'
                }`}
              >
                <div className="flex items-center justify-between text-[10px] text-[#8A8F94]">
                  <span>0{idx + 1}</span>
                  {typeof stageMs === 'number' && stageMs > 0 && (
                    <span>{stageMs.toFixed(0)}ms</span>
                  )}
                </div>
                <span className="font-medium text-xs truncate mt-0.5">
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
