import React from 'react';

const LANG_NAMES = {
  mr: 'मराठी (Marathi)',
  en: 'English',
  hi: 'हिंदी (Hindi)',
  ta: 'தமிழ் (Tamil)',
  te: 'తెలుగు (Telugu)',
  kn: 'ಕನ್ನಡ (Kannada)',
  gu: 'ગુજરાતી (Gujarati)',
  bn: 'বাংলা (Bengali)',
};

export default function TranscriptCard({ transcript, languageDetected, sttLatency, isVoice }) {
  if (!transcript) return null;

  const langLabel = LANG_NAMES[languageDetected] || (languageDetected ? languageDetected.toUpperCase() : 'Auto');

  return (
    <div className="w-full paithani-card p-4 border-paithani-border/80 my-3 relative overflow-hidden">
      {/* Top indicator bar */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded-md bg-paithani-maroon/40 text-paithani-gold-light">
            {isVoice ? (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            )}
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-paithani-ivory-dim">
            {isVoice ? 'ध्वनी लिपीकरण (STT Transcript)' : 'विचारलेला प्रश्न (Input Query)'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {/* Detected Language Pill */}
          <span className="px-2 py-0.5 rounded-full bg-paithani-surface border border-paithani-gold/30 text-paithani-gold-light text-[11px] font-medium">
            {langLabel}
          </span>

          {/* STT Latency if available */}
          {sttLatency > 0 && (
            <span className="hidden sm:inline-block px-2 py-0.5 rounded-md bg-paithani-card border border-paithani-border text-paithani-ivory-dim text-[11px] font-mono">
              STT: {sttLatency.toFixed(1)}ms
            </span>
          )}
        </div>
      </div>

      {/* Transcript Text */}
      <p className="font-marathi text-base sm:text-lg text-paithani-ivory font-medium leading-relaxed pl-1">
        &ldquo;{transcript}&rdquo;
      </p>
    </div>
  );
}
