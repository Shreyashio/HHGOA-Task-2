import React, { useState } from 'react';

const LANG_NAMES = {
  'mr-IN': 'Marathi',
  'mr': 'Marathi',
  'en-IN': 'English',
  'en': 'English',
  'hi-IN': 'Hindi',
  'hi': 'Hindi',
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
    model,
    language_detected,
    sources = [],
    latency = {},
  } = result;

  const langLabel = LANG_NAMES[language_detected] || (language_detected ? language_detected.toUpperCase() : 'Auto');
  const searchPipelineMs = latency?.search_pipeline_ms || ((latency?.retrieval_ms || 0) + (latency?.reranking_ms || 0)) || 0;

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
    if (language_detected?.startsWith('mr')) {
      utterance.lang = 'mr-IN';
    } else if (language_detected?.startsWith('hi')) {
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
    <div className="w-full surface-card p-5 sm:p-6 my-4 animate-fadeIn relative">
      {/* ── QUESTION HEADER ──────────────────────────────────────────────────────── */}
      {transcript && (
        <div className="pb-3.5 mb-3.5 border-b border-white/[0.06]">
          <div className="flex items-center justify-between text-xs text-[#8A8F94] mb-1">
            <span className="font-medium text-[11px] uppercase tracking-wider">
              {isVoice ? 'Question' : 'Query'} &bull; {langLabel}
            </span>
            {typeof latency?.stt_ms === 'number' && latency.stt_ms > 0 && (
              <span className="text-[11px] text-[#8A8F94]">
                Audio STT: {latency.stt_ms.toFixed(0)}ms
              </span>
            )}
          </div>
          <p className="text-base sm:text-lg text-[#F5F0E6] font-medium leading-relaxed">
            &ldquo;{transcript}&rdquo;
          </p>
        </div>
      )}

      {/* ── ANSWER BODY ─────────────────────────────────────────────────────────── */}
      <div className="py-1">
        <div className="flex items-center justify-between gap-2 mb-2 text-xs text-[#8A8F94]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF6B35]" />
            <span className="font-medium text-[11px] uppercase tracking-wider text-[#F5F0E6]">
              Answer
            </span>
            {grounded ? (
              <span className="text-[11px] text-emerald-400 font-medium">
                (Grounded in MSMARCO)
              </span>
            ) : (
              <span className="text-[11px] text-[#8A8F94]">
                (General Knowledge)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {'speechSynthesis' in window && (
              <button
                type="button"
                onClick={handleSpeak}
                className="px-2 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-[#F5F0E6] text-xs transition-colors flex items-center gap-1"
                title="Listen to answer"
              >
                <svg className="w-3.5 h-3.5 text-[#FF6B35]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                </svg>
                <span>{isSpeaking ? 'Stop' : 'Listen'}</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleCopy}
              className="px-2 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-[#8A8F94] hover:text-[#F5F0E6] text-xs transition-colors"
              title="Copy to clipboard"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>

        <p className="text-sm sm:text-base text-[#F5F0E6] leading-relaxed whitespace-pre-line">
          {answer}
        </p>
      </div>

      {/* ── SOURCES ACCORDION (Sand Gold used strictly here for scores) ──────────── */}
      {sources && sources.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/[0.06]">
          <button
            type="button"
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="w-full flex items-center justify-between text-left text-xs text-[#8A8F94] hover:text-[#F5F0E6] transition-colors py-1"
          >
            <span className="font-medium text-[11px] uppercase tracking-wider">
              Sources ({sources.length} passages retrieved)
            </span>
            <svg
              className={`w-3.5 h-3.5 transition-transform duration-200 ${sourcesOpen ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {sourcesOpen && (
            <div className="mt-2.5 space-y-2">
              {sources.map((src, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-[#161B22]/60 border border-white/[0.04] text-xs"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5 text-[11px] text-[#8A8F94]">
                    <span className="text-[#F5F0E6] font-medium truncate">
                      {src.doc_id || `Passage #${idx + 1}`}
                    </span>
                    {src.score !== undefined && (
                      <span className="text-[#FFB347] font-medium">
                        Score: {Number(src.score).toFixed(3)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#8A8F94] leading-relaxed italic">
                    &ldquo;{src.snippet}&rdquo;
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
