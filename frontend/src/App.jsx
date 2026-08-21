import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import WarliMic from './components/WarliMic';
import TextFallback from './components/TextFallback';
import QAUnifiedCard from './components/QAUnifiedCard';
import PipelineStrip from './components/PipelineStrip';
import ErrorBanner from './components/ErrorBanner';
import { checkBackendHealth, queryVoice, queryText } from './services/api';
import './index.css';

function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [mockMode, setMockMode] = useState(false);
  const [strategy, setStrategy] = useState('sentence');
  const [selectedLang, setSelectedLang] = useState('en-IN');

  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isVoice, setIsVoice] = useState(false);
  const [lastAction, setLastAction] = useState(null);

  const probeHealth = useCallback(async () => {
    const res = await checkBackendHealth();
    setBackendOnline(res.online);
  }, []);

  useEffect(() => {
    probeHealth();
    const interval = setInterval(probeHealth, 10000);
    return () => clearInterval(interval);
  }, [probeHealth]);

  const handleAudioRecorded = async (audioBlob) => {
    setIsProcessing(true);
    setCurrentStage('stt');
    setError(null);
    setIsVoice(true);
    setLastAction({ type: 'voice', data: audioBlob });

    try {
      const data = await queryVoice({
        audioBlob,
        strategy,
        lang: selectedLang,
        mock: mockMode,
        onProgress: (stage) => setCurrentStage(stage),
      });

      setResult(data);
      setCurrentStage(null);
    } catch (err) {
      console.error("Voice query failed:", err);
      setError(err.message || 'Voice query failed. Please check connection or retry.');
      setCurrentStage(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendText = async (textQuery) => {
    setIsProcessing(true);
    setCurrentStage('retrieve');
    setError(null);
    setIsVoice(false);
    setLastAction({ type: 'text', data: textQuery });

    try {
      const data = await queryText({
        query: textQuery,
        strategy,
        langFilter: selectedLang,
        mock: mockMode,
        onProgress: (stage) => setCurrentStage(stage),
      });

      setResult(data);
      setCurrentStage(null);
    } catch (err) {
      console.error("Text query failed:", err);
      setError(err.message || 'Text query failed. Please check connection.');
      setCurrentStage(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRetry = () => {
    if (!lastAction) return;
    if (lastAction.type === 'voice') {
      handleAudioRecorded(lastAction.data);
    } else {
      handleSendText(lastAction.data);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0B0E11] text-[#F5F0E6]">
      {/* ── 1. HEADER (Only wordmark + clean language selector) ────────────────── */}
      <Header
        selectedLang={selectedLang}
        setSelectedLang={setSelectedLang}
      />

      {/* ── MAIN CONTENT (Tighter, denser spacing) ──────────────────────────────── */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 pt-5 pb-8 flex flex-col items-center">
        {/* Hero Section (Clean serif title, tight copy, zero badges) */}
        <div className="text-center mb-4">
          <h2 className="font-marathi text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E6]">
            मातृभाषा
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-[#8A8F94] max-w-md mx-auto">
            Sub-200ms grounded question answering on MSMARCO-XI.
          </p>
        </div>

        {/* ── 2. CENTRAL INTERACTION CARD (Mic + Natural Secondary Text Bar) ──────── */}
        <div className="w-full surface-card p-4 sm:p-5 flex flex-col items-center">
          {/* Breathing single-ring mic */}
          <WarliMic
            onAudioRecorded={handleAudioRecorded}
            isProcessing={isProcessing}
            disabled={!backendOnline && !mockMode}
          />

          {/* Natural secondary text input (no divider line) */}
          <TextFallback
            onSendText={handleSendText}
            isProcessing={isProcessing}
          />
        </div>

        {/* Error notification if any */}
        {error && (
          <ErrorBanner
            error={error}
            onRetry={handleRetry}
            onSwitchMock={() => {
              setMockMode(true);
              setError(null);
            }}
          />
        )}

        {/* ── 3. QUESTION + ANSWER CARD (Single Bordered Physical Frame) ──────────── */}
        {result && (
          <QAUnifiedCard
            result={result}
            isVoice={isVoice}
          />
        )}

        {/* ── 4. QUIET FOOTER PIPELINE STRIP ──────────────────────────────────────── */}
        <PipelineStrip
          currentStage={currentStage}
          latencyData={result?.latency}
          isProcessing={isProcessing}
        />
      </main>

      {/* ── 5. SINGLE QUIET MONOSPACE DEBUG STRIP AT PAGE BOTTOM ─────────────────── */}
      <footer className="w-full border-t border-white/[0.05] py-3 text-[11px] font-mono text-[#8A8F94]">
        <div className="max-w-3xl mx-auto px-4 flex flex-wrap items-center justify-between gap-y-2 gap-x-4">
          {/* System status & dev parameters in ONE unified line */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* The ONLY teal accent on the entire page: system status dot */}
            <span className="flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendOnline ? 'bg-[#1DBFA3]' : 'bg-amber-500'
                }`}
              />
              <span className={backendOnline ? 'text-[#F5F0E6]' : 'text-amber-400'}>
                {backendOnline ? 'api: online (:8000)' : 'api: offline'}
              </span>
            </span>

            <span>&bull;</span>

            {/* Inline Strategy Select */}
            <span className="flex items-center gap-1">
              <span>strategy:</span>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="bg-transparent text-[#F5F0E6] hover:underline cursor-pointer outline-none font-mono"
              >
                <option value="sentence" className="bg-[#12161B] text-[#F5F0E6]">sentence</option>
                <option value="fixed" className="bg-[#12161B] text-[#F5F0E6]">fixed (256-tok)</option>
                <option value="metadata" className="bg-[#12161B] text-[#F5F0E6]">metadata-rich</option>
              </select>
            </span>

            <span>&bull;</span>

            {/* Inline Mock Toggle */}
            <button
              type="button"
              onClick={() => setMockMode(!mockMode)}
              className="hover:text-[#F5F0E6] transition-colors"
            >
              mock: <span className={mockMode ? 'text-[#FFB347]' : 'text-[#8A8F94]'}>{mockMode ? 'on' : 'off'}</span>
            </button>
          </div>

          {/* Minimal Event attribution */}
          <div className="text-[#8A8F94]/70">
            Hacker House Goa 2026
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
