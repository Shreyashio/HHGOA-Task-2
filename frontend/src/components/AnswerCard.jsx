import React, { useState } from 'react';

export default function AnswerCard({
  answer,
  grounded,
  confidence,
  guardrailPassed,
  guardrailReason,
  model,
  languageDetected,
  mock,
}) {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  if (!answer) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(answer).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleSpeak = () => {
    if (!('speechSynthesis' in window)) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel(); // Reset any existing speech
    const utterance = new SpeechSynthesisUtterance(answer);
    
    // Attempt language matching for Marathi or English
    if (languageDetected === 'mr') {
      utterance.lang = 'mr-IN';
    } else if (languageDetected === 'hi') {
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
    <div className="w-full paithani-card p-5 sm:p-6 border-paithani-gold/40 relative overflow-hidden my-3 shadow-2xl">
      {/* Decorative Gold Header Bar */}
      <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-paithani-maroon via-paithani-gold to-paithani-maroon" />

      {/* Card Header with Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-paithani-border/60">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-paithani-maroon/80 border border-paithani-gold/40 flex items-center justify-center text-paithani-gold-light">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-marathi font-bold text-base sm:text-lg text-paithani-ivory leading-none">
              सत्यापित उत्तर (Verified Answer)
            </h3>
            <span className="text-[10px] text-paithani-ivory-dim">
              MSMARCO-XI Grounded Response
            </span>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
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
              Unverified / Refusal
            </span>
          )}

          {/* Guardrail Flag */}
          {guardrailPassed ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-paithani-surface border border-paithani-border text-paithani-ivory-dim text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Guardrail Pass
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-950 border border-red-500/40 text-red-300 text-[10px]" title={guardrailReason}>
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              Guardrail Flag
            </span>
          )}

          {/* Confidence Score */}
          {confidence !== undefined && (
            <span className="px-2 py-0.5 rounded-md bg-paithani-surface border border-paithani-border text-paithani-gold-light text-[10px] font-mono">
              Conf: {(confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* Main Answer Body */}
      <div className="prose prose-invert max-w-none">
        <p className="font-marathi text-base sm:text-lg text-paithani-ivory leading-relaxed whitespace-pre-line">
          {answer}
        </p>
      </div>

      {/* Footer Controls: Model tag, TTS Readout, and Copy */}
      <div className="mt-5 pt-3 border-t border-paithani-border/50 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-paithani-ivory-dim">
          <span className="text-[11px]">Model:</span>
          <span className="font-mono text-paithani-gold-light text-[11px] bg-paithani-surface px-2 py-0.5 rounded border border-paithani-border">
            {model || 'llama-3.1-8b-instant (Groq)'}
          </span>
          {mock && (
            <span className="text-[10px] text-amber-400 font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-500/30">
              Mock Run
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Audio TTS Speech Playback Button */}
          {'speechSynthesis' in window && (
            <button
              type="button"
              onClick={handleSpeak}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                isSpeaking
                  ? 'bg-paithani-maroon text-paithani-gold-light border-paithani-gold shadow-md animate-pulse'
                  : 'bg-paithani-surface hover:bg-paithani-cardHover text-paithani-ivory-muted hover:text-paithani-ivory border-paithani-border'
              }`}
              title="Speak answer using browser text-to-speech"
            >
              {isSpeaking ? (
                <>
                  <svg className="w-3.5 h-3.5 text-paithani-gold-light" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="4" width="4" height="16" />
                    <rect x="14" y="4" width="4" height="16" />
                  </svg>
                  <span>थांबवा (Pause)</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 text-paithani-gold-light" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                  <span>वाचून दाखवा (Listen)</span>
                </>
              )}
            </button>
          )}

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-paithani-surface hover:bg-paithani-cardHover text-paithani-ivory-muted hover:text-paithani-ivory border border-paithani-border text-xs font-medium transition-all"
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
    </div>
  );
}
