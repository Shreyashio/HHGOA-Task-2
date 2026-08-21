import React, { useState } from 'react';

const LANG_NAMES = {
  mr: 'Marathi',
  en: 'English',
  hi: 'Hindi',
  ta: 'Tamil',
  te: 'Telugu',
  kn: 'Kannada',
  gu: 'Gujarati',
  bn: 'Bengali',
};

export default function QAUnifiedCard({ result, isVoice }) {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (!result) return null;

  const {
    transcript,
    answer,
    grounded,
    confidence,
    guardrail_passed,
    guardrail_reason,
    model,
    language_detected,
    mock,
    sources = [],
    latency = {},
  } = result;

  const langLabel = LANG_NAMES[language_detected] || (language_detected ? language_detected.toUpperCase() : 'Auto');
  const totalMs = latency?.total_ms || 0;
  const searchPipelineMs = latency?.search_pipeline_ms || ((latency?.retrieval_ms || 0) + (latency?.reranking_ms || 0)) || 0;
  const isSearchSub200 = searchPipelineMs < 200;

  // Latency bar percentages
  const sttPct = totalMs > 0 ? ((latency.stt_ms || 0) / totalMs) * 100 : 0;
  const retPct = totalMs > 0 ? ((latency.retrieval_ms || 0) / totalMs) * 100 : 0;
  const rerankPct = totalMs > 0 ? ((latency.reranking_ms || 0) / totalMs) * 100 : 0;
  const genPct = totalMs > 0 ? ((latency.generation_ms || 0) / totalMs) * 100 : 0;
  const otherPct = Math.max(0, 100 - (sttPct + retPct + rerankPct + genPct));

  const handleCopy = () => {
    if (!answer) return;
    navigator.clipboard.writeText(answer).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleSpeak = () => {
    if (!('speechSynthesis' in window) || !answer) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(answer);
    
    if (language_detected === 'mr') {
      utterance.lang = 'mr-IN';
    } else if (language_detected === 'hi') {
      utterance.lang = 'hi-IN';
    } else {
      utterance.lang = 'en-US';
    }
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="w-full hhg-card p-5 sm:p-6 border-hhg-coral/30 relative overflow-hidden my-4 shadow-2xl animate-fadeIn">
      {/* Decorative Top Sunrise / Teal Accent Line */}
      <div className="absolute top-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-hhg-coral via-hhg-teal to-hhg-gold opacity-90" />

      {/* ── CARD HEADER & ACTION CONTROLS ────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-4 mb-4 border-b border-hhg-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-hhg-coral/20 border border-hhg-coral/40 flex items-center justify-center text-hhg-coral">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-base sm:text-lg text-hhg-sand leading-tight">
              Verified Response
            </h3>
            <span className="text-[10px] text-hhg-sand-muted font-mono">
              MSMARCO-XI Grounded Knowledge
            </span>
          </div>
        </div>

        {/* Status Indicators & Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Grounding Badge */}
          {grounded ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-[11px] font-medium">
              <svg className="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Grounded
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 text-[11px] font-medium">
              <svg className="w-3 h-3 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              General Knowledge
            </span>
          )}

          {/* Confidence Badge */}
          {confidence !== undefined && confidence !== null && (
            <span className="px-2 py-0.5 rounded-md bg-hhg-surface border border-hhg-border text-hhg-gold text-[11px] font-mono">
              Conf: {(confidence * 100).toFixed(0)}%
            </span>
          )}

          {/* Audio TTS Speech Playback Button */}
          {'speechSynthesis' in window && (
            <button
              type="button"
              onClick={handleSpeak}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium transition-all ${
                isSpeaking
                  ? 'bg-hhg-coral text-[#0B0E11] border-hhg-coral shadow-md animate-pulse font-semibold'
                  : 'bg-hhg-surface hover:bg-hhg-cardHover text-hhg-sand-muted hover:text-hhg-sand border-hhg-border'
              }`}
              title="Speak answer via browser text-to-speech"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
              <span>{isSpeaking ? 'Pause' : 'Listen'}</span>
            </button>
          )}

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-hhg-surface hover:bg-hhg-cardHover text-hhg-sand-muted hover:text-hhg-sand border border-hhg-border text-xs font-medium transition-all"
            title="Copy answer to clipboard"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-emerald-300">Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── SECTION 1: QUESTION / TRANSCRIPT (Stacked inside frame) ────────────────── */}
      {transcript && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-hhg-surface/90 border border-hhg-border mb-4">
          <div className="flex items-center justify-between mb-1.5 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-hhg-card border border-hhg-border text-hhg-teal">
                {isVoice ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                ) : (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                )}
              </span>
              <span className="font-mono font-semibold uppercase tracking-wider text-hhg-sand-muted">
                {isVoice ? 'Audio Transcript' : 'Input Query'}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-hhg-card border border-hhg-border text-hhg-sand text-[11px] font-mono">
                {langLabel}
              </span>
              {typeof latency.stt_ms === 'number' && latency.stt_ms > 0 && (
                <span className="hidden sm:inline-block px-2 py-0.5 rounded bg-hhg-card border border-hhg-border text-hhg-teal text-[11px] font-mono">
                  STT: {latency.stt_ms.toFixed(1)}ms
                </span>
              )}
            </div>
          </div>

          <p className="text-base sm:text-lg text-hhg-sand font-medium leading-relaxed italic">
            &ldquo;{transcript}&rdquo;
          </p>
        </div>
      )}

      {/* ── SECTION 2: ANSWER BODY (Stacked inside frame) ─────────────────────────── */}
      <div className="py-2">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full bg-hhg-coral" />
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-hhg-sand-muted">
            Answer
          </span>
        </div>
        <p className="text-base sm:text-lg text-hhg-sand leading-relaxed whitespace-pre-line font-normal">
          {answer}
        </p>

        {/* Model info footer */}
        <div className="mt-3 flex items-center gap-2 text-xs text-hhg-sand-dim font-mono">
          <span>Model:</span>
          <span className="text-hhg-teal bg-hhg-surface px-2 py-0.5 rounded border border-hhg-border">
            {model || 'llama-3.1-8b-instant (Groq)'}
          </span>
          {mock && (
            <span className="text-amber-400 font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-500/30 text-[10px]">
              Mock Run
            </span>
          )}
        </div>
      </div>

      {/* ── SECTION 3: SOURCES ACCORDION (Sub-section inside card) ──────────────────── */}
      {sources && sources.length > 0 && (
        <div className="mt-4 border-t border-hhg-border/60 pt-3">
          <button
            type="button"
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-hhg-surface hover:bg-hhg-cardHover border border-hhg-border transition-colors flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-hhg-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <div>
                <h4 className="font-semibold text-xs text-hhg-sand leading-tight">
                  Source Chunks Used ({sources.length})
                </h4>
                <p className="text-[10px] text-hhg-sand-muted">
                  Retrieved MSMARCO-XI passages for grounding
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-hhg-card border border-hhg-border text-[11px] font-mono text-hhg-teal">
                {sources.length} chunks
              </span>
              <svg
                className={`w-4 h-4 text-hhg-sand-muted transition-transform duration-200 ${
                  sourcesOpen ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          {sourcesOpen && (
            <div className="mt-2.5 space-y-2.5">
              {sources.map((src, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-hhg-surface/80 border border-hhg-border hover:border-hhg-coral/30 transition-all text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-1.5 pb-2 mb-2 border-b border-hhg-border/50 text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-hhg-coral bg-hhg-card px-1.5 py-0.5 rounded font-mono">
                        #{src.source_index !== undefined ? src.source_index + 1 : idx + 1}
                      </span>
                      <span className="font-mono text-hhg-sand font-semibold truncate max-w-[160px] sm:max-w-none">
                        {src.doc_id || `DOC_${idx + 1}`}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {src.lang && (
                        <span className="px-2 py-0.5 rounded bg-hhg-card text-hhg-sand-muted font-mono uppercase text-[10px]">
                          {src.lang}
                        </span>
                      )}
                      {src.score !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-hhg-teal/10 border border-hhg-teal/40 text-hhg-teal font-mono font-medium text-[10px]">
                          Score: {Number(src.score).toFixed(3)}
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-hhg-sand text-xs sm:text-sm leading-relaxed whitespace-pre-line italic text-hhg-sand-muted pl-1">
                    &ldquo;{src.snippet}&rdquo;
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── SECTION 4: LATENCY TELEMETRY (Sub-section inside card) ────────────────── */}
      {latency && (
        <div className="mt-4 border-t border-hhg-border/60 pt-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-hhg-sand-muted">
                Latency Breakdown
              </span>
            </div>

            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium ${
                isSearchSub200
                  ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300'
                  : 'bg-amber-950/80 border border-amber-500/50 text-amber-300'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isSearchSub200 ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              Search Pipeline: {searchPipelineMs.toFixed(1)}ms {isSearchSub200 ? '(< 200ms Target Met ✓)' : ''}
            </span>
          </div>

          {/* Stacked Latency Distribution Bar */}
          <div className="w-full h-2 bg-hhg-surface rounded-full overflow-hidden flex shadow-inner mb-2.5">
            {sttPct > 0 && (
              <div style={{ width: `${sttPct}%` }} className="bg-amber-500 hover:opacity-90 transition-all" title={`STT: ${latency.stt_ms?.toFixed(1)}ms`} />
            )}
            {retPct > 0 && (
              <div style={{ width: `${retPct}%` }} className="bg-hhg-coral hover:opacity-90 transition-all" title={`Retrieval: ${latency.retrieval_ms?.toFixed(1)}ms`} />
            )}
            {rerankPct > 0 && (
              <div style={{ width: `${rerankPct}%` }} className="bg-hhg-teal hover:opacity-90 transition-all" title={`Rerank: ${latency.reranking_ms?.toFixed(1)}ms`} />
            )}
            {genPct > 0 && (
              <div style={{ width: `${genPct}%` }} className="bg-hhg-gold hover:opacity-90 transition-all" title={`Generation: ${latency.generation_ms?.toFixed(1)}ms`} />
            )}
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5 text-center font-mono">
            <div className="p-1.5 rounded-lg bg-hhg-surface border border-hhg-border">
              <p className="text-[9px] text-hhg-sand-muted uppercase">STT Audio</p>
              <p className="font-bold text-xs text-amber-400 mt-0.5">
                {latency.stt_ms ? `${latency.stt_ms.toFixed(0)} ms` : '—'}
              </p>
            </div>

            <div className="p-1.5 rounded-lg bg-hhg-surface border border-hhg-border">
              <p className="text-[9px] text-hhg-sand-muted uppercase">Vector Search</p>
              <p className="font-bold text-xs text-hhg-coral mt-0.5">
                {latency.retrieval_ms ? `${latency.retrieval_ms.toFixed(0)} ms` : '—'}
              </p>
            </div>

            <div className="p-1.5 rounded-lg bg-hhg-surface border border-hhg-border">
              <p className="text-[9px] text-hhg-sand-muted uppercase">BM25 Rerank</p>
              <p className="font-bold text-xs text-hhg-teal mt-0.5">
                {latency.reranking_ms ? `${latency.reranking_ms.toFixed(0)} ms` : '—'}
              </p>
            </div>

            <div className="p-1.5 rounded-lg bg-hhg-surface border border-hhg-border">
              <p className="text-[9px] text-hhg-sand-muted uppercase">Search Pipe</p>
              <p className="font-bold text-xs text-emerald-400 mt-0.5">
                {searchPipelineMs.toFixed(0)} ms
              </p>
            </div>

            <div className="p-1.5 rounded-lg bg-hhg-surface border border-hhg-border">
              <p className="text-[9px] text-hhg-sand-muted uppercase">LLM Gen</p>
              <p className="font-bold text-xs text-hhg-sand mt-0.5">
                {latency.generation_ms ? `${latency.generation_ms.toFixed(0)} ms` : '—'}
              </p>
            </div>

            <div className="p-1.5 rounded-lg bg-hhg-coral/15 border border-hhg-coral/40 text-hhg-coral">
              <p className="text-[9px] uppercase font-semibold">Total E2E</p>
              <p className="font-bold text-xs mt-0.5">
                {totalMs ? `${totalMs.toFixed(0)} ms` : '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
