import React, { Component, StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-[#14100F] text-[#F3E9D8] p-6 text-center">
          <div className="max-w-md w-full p-6 rounded-2xl bg-[#1C1716] border border-[#C9A227]/40 shadow-2xl space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-950/80 border border-red-500/50 flex items-center justify-center mx-auto text-red-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="font-marathi text-xl font-bold text-[#F3E9D8]">काहीतरी त्रुटी आली (Application Error)</h2>
            <p className="text-xs text-[#F3E9D8]/70 leading-relaxed font-mono bg-[#14100F] p-3 rounded-lg border border-[#3A2D28] text-left overflow-auto max-h-32">
              {this.state.error?.message || "Unknown rendering error"}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="w-full py-2.5 rounded-xl bg-[#7A1F2B] hover:bg-[#9B2837] border border-[#C9A227]/50 text-[#F3E9D8] text-xs font-semibold uppercase tracking-wider transition-all"
            >
              पुन्हा लोड करा (Reload Page)
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
