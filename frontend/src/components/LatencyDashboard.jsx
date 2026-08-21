import React from 'react';

export default function LatencyDashboard({ latency }) {
  if (!latency) return null;

  const total = latency.total_ms || 0;
  const searchPipeline = latency.search_pipeline_ms || (latency.retrieval_ms + latency.reranking_ms) || 0;
  const isSearchSub200 = searchPipeline < 200;

  // Percentage calculations for stacked bar
  const sttPct = total > 0 ? ((latency.stt_ms || 0) / total) * 100 : 0;
  const retPct = total > 0 ? ((latency.retrieval_ms || 0) / total) * 100 : 0;
  const rerankPct = total > 0 ? ((latency.reranking_ms || 0) / total) * 100 : 0;
  const genPct = total > 0 ? ((latency.generation_ms || 0) / total) * 100 : 0;
  const otherPct = Math.max(0, 100 - (sttPct + retPct + rerankPct + genPct));

  return (
    <div className="w-full paithani-card p-4 sm:p-5 border-paithani-border/80 my-3">
      {/* Title & Target Status */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-2 border-b border-paithani-border/50">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded-md bg-paithani-surface text-paithani-gold-light">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>
          <div>
            <h4 className="font-marathi font-bold text-sm text-paithani-ivory leading-tight">
              कार्यक्षमता व वेग (Request Latency Telemetry)
            </h4>
            <p className="text-[11px] text-paithani-ivory-dim">
              Fine-grained latency metrics for this interaction
            </p>
          </div>
        </div>

        {/* Search Pipeline Target Badge */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
              isSearchSub200
                ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300'
                : 'bg-amber-950/80 border border-amber-500/50 text-amber-300'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isSearchSub200 ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            Search Pipeline: {searchPipeline.toFixed(1)}ms {isSearchSub200 ? '(< 200ms Target Met ✓)' : ''}
          </span>
        </div>
      </div>

      {/* Stacked Latency Distribution Bar */}
      <div className="mb-4">
        <div className="w-full h-2.5 bg-paithani-surface rounded-full overflow-hidden flex shadow-inner">
          {sttPct > 0 && (
            <div
              style={{ width: `${sttPct}%` }}
              className="bg-amber-500 hover:opacity-90 transition-all"
              title={`STT: ${latency.stt_ms?.toFixed(1)}ms (${sttPct.toFixed(1)}%)`}
            />
          )}
          {retPct > 0 && (
            <div
              style={{ width: `${retPct}%` }}
              className="bg-paithani-gold hover:opacity-90 transition-all"
              title={`Retrieval: ${latency.retrieval_ms?.toFixed(1)}ms (${retPct.toFixed(1)}%)`}
            />
          )}
          {rerankPct > 0 && (
            <div
              style={{ width: `${rerankPct}%` }}
              className="bg-blue-400 hover:opacity-90 transition-all"
              title={`Rerank: ${latency.reranking_ms?.toFixed(1)}ms (${rerankPct.toFixed(1)}%)`}
            />
          )}
          {genPct > 0 && (
            <div
              style={{ width: `${genPct}%` }}
              className="bg-paithani-maroon-light hover:opacity-90 transition-all"
              title={`LLM Gen: ${latency.generation_ms?.toFixed(1)}ms (${genPct.toFixed(1)}%)`}
            />
          )}
          {otherPct > 0 && (
            <div
              style={{ width: `${otherPct}%` }}
              className="bg-gray-600 hover:opacity-90 transition-all"
              title={`Guardrails / Misc: ${otherPct.toFixed(1)}%`}
            />
          )}
        </div>

        {/* Legend */}
        <div className="mt-2 flex flex-wrap items-center justify-between text-[10px] text-paithani-ivory-dim gap-y-1">
          {latency.stt_ms > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              STT ({latency.stt_ms.toFixed(0)}ms)
            </span>
          )}
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-paithani-gold" />
            Vector Retrieve ({latency.retrieval_ms?.toFixed(0)}ms)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            BM25 Rerank ({latency.reranking_ms?.toFixed(0)}ms)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-paithani-maroon-light" />
            LLM Generation ({latency.generation_ms?.toFixed(0)}ms)
          </span>
        </div>
      </div>

      {/* Grid of Individual Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-center">
        <div className="p-2 rounded-xl bg-paithani-surface/80 border border-paithani-border">
          <p className="text-[10px] text-paithani-ivory-dim uppercase tracking-wider">STT Audio</p>
          <p className="font-mono font-bold text-sm text-amber-400 mt-0.5">
            {latency.stt_ms ? `${latency.stt_ms.toFixed(1)} ms` : '—'}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-paithani-surface/80 border border-paithani-border">
          <p className="text-[10px] text-paithani-ivory-dim uppercase tracking-wider">Vector Search</p>
          <p className="font-mono font-bold text-sm text-paithani-gold-light mt-0.5">
            {latency.retrieval_ms ? `${latency.retrieval_ms.toFixed(1)} ms` : '—'}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-paithani-surface/80 border border-paithani-border">
          <p className="text-[10px] text-paithani-ivory-dim uppercase tracking-wider">BM25 Rerank</p>
          <p className="font-mono font-bold text-sm text-blue-300 mt-0.5">
            {latency.reranking_ms ? `${latency.reranking_ms.toFixed(1)} ms` : '—'}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-paithani-surface/80 border border-paithani-border">
          <p className="text-[10px] text-paithani-ivory-dim uppercase tracking-wider">Search Pipeline</p>
          <p className="font-mono font-bold text-sm text-emerald-400 mt-0.5">
            {searchPipeline.toFixed(1)} ms
          </p>
        </div>

        <div className="p-2 rounded-xl bg-paithani-surface/80 border border-paithani-border">
          <p className="text-[10px] text-paithani-ivory-dim uppercase tracking-wider">LLM Generation</p>
          <p className="font-mono font-bold text-sm text-paithani-ivory mt-0.5">
            {latency.generation_ms ? `${latency.generation_ms.toFixed(1)} ms` : '—'}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-paithani-maroon/30 border border-paithani-maroon text-paithani-gold-light">
          <p className="text-[10px] uppercase tracking-wider font-semibold">Total E2E</p>
          <p className="font-mono font-bold text-sm text-paithani-gold-light mt-0.5">
            {total ? `${total.toFixed(1)} ms` : '—'}
          </p>
        </div>
      </div>
    </div>
  );
}
