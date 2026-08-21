import React from 'react';

export default function ErrorBanner({ error, onRetry, onSwitchMock }) {
  if (!error) return null;

  return (
    <div className="w-full hhg-card border-red-500/50 bg-red-950/30 p-4 my-3 text-red-200 shadow-xl animate-fadeIn">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-red-900/50 border border-red-500/40 text-red-300 flex-shrink-0 mt-0.5">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>

        <div className="flex-1">
          <h4 className="font-semibold text-sm text-red-200">
            Request Encountered an Issue
          </h4>
          <p className="text-xs text-red-300/90 mt-1 leading-relaxed font-mono">
            {error}
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="px-3 py-1 rounded-lg bg-red-900 hover:bg-red-800 border border-red-500/50 text-white text-xs font-medium transition-all font-mono"
              >
                Retry Request
              </button>
            )}

            {onSwitchMock && (
              <button
                type="button"
                onClick={onSwitchMock}
                className="px-3 py-1 rounded-lg bg-hhg-surface hover:bg-hhg-cardHover border border-hhg-gold/50 text-hhg-gold text-xs font-medium transition-all font-mono"
              >
                Switch to Offline Mock Mode
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
