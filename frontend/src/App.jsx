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
  const [selectedLang, setSelectedLang] = useState('en-IN'); // Defaults to English ('en-IN'), options: 'en-IN', 'mr-IN', 'hi-IN'

  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isVoice, setIsVoice] = useState(false);
  const [lastAction, setLastAction] = useState(null);

  // Check backend health periodically
  const probeHealth = useCallback(async () => {
    const res = await checkBackendHealth();
    setBackendOnline(res.online);
  }, []);

  useEffect(() => {
    probeHealth();
    const interval = setInterval(probeHealth, 10000);
    return () => clearInterval(interval);
  }, [probeHealth]);

  // Voice recording handler
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
      setError(err.message || 'Voice query failed. Check backend connection or API keys.');
      setCurrentStage(null);
    } finally {
      setIsProcessing(false);
    }
  };

  // Text search handler
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
      setError(err.message || 'Text query failed. Check backend connection.');
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
    <div className="min-h-screen flex flex-col bg-hhg-bg text-hhg-sand">
      {/* ── 1. HEADER (मातृभाषा wordmark + unobtrusive language selector + status) ── */}
      <Header
        backendOnline={backendOnline}
        mockMode={mockMode}
        setMockMode={setMockMode}
        strategy={strategy}
        setStrategy={setStrategy}
        selectedLang={selectedLang}
        setSelectedLang={setSelectedLang}
      />

      {/* ── MAIN CONTENT CONTAINER ──────────────────────────────────────────────── */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 sm:py-8 flex flex-col items-center">
        {/* Hero Section */}
        <div className="text-center max-w-2xl mx-auto mb-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-hhg-surface border border-hhg-border text-hhg-teal text-xs font-mono font-medium tracking-wide mb-3">
            <span className="w-2 h-2 rounded-full bg-hhg-teal animate-pulse" />
            <span>Hacker House Goa 2026</span>
            <span className="text-hhg-sand-dim">&bull;</span>
            <span className="text-hhg-coral">Task #2</span>
          </div>

          <h2 className="font-marathi text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-hhg-sand">
            <span className="hhg-coral-gradient">मातृभाषा</span>
          </h2>

          <p className="mt-2 text-xs sm:text-sm text-hhg-sand-muted max-w-lg mx-auto leading-relaxed">
            Voice-first grounded question answering on{' '}
            <strong className="text-hhg-sand font-mono">MSMARCO-XI</strong> with{' '}
            <strong className="text-emerald-400 font-mono">&lt;200ms search latency</strong>.
          </p>
        </div>

        {/* ── 2. CENTRAL MIC BUTTON + 3. TEXT INPUT FALLBACK ──────────────────────── */}
        <div className="w-full hhg-card p-4 sm:p-6 border-hhg-border my-2 relative">
          <WarliMic
            onAudioRecorded={handleAudioRecorded}
            isProcessing={isProcessing}
            disabled={!backendOnline && !mockMode}
          />

          {/* Divider */}
          <div className="relative my-4 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-hhg-border" />
            </div>
            <span className="relative px-3 bg-hhg-card text-[11px] font-mono uppercase tracking-wider text-hhg-sand-muted font-medium">
              Or Enter Text
            </span>
          </div>

          {/* Text Input Fallback */}
          <TextFallback
            onSendText={handleSendText}
            isProcessing={isProcessing}
          />
        </div>

        {/* Error Notification */}
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

        {/* ── 4. COMBINED QUESTION + ANSWER CARD (Single Bordered Unit) ────────────── */}
        {result && (
          <QAUnifiedCard
            result={result}
            isVoice={isVoice}
          />
        )}

        {/* ── 5. FOOTER PIPELINE STRIP (Moved from top, compact & quiet) ───────────── */}
        <PipelineStrip
          currentStage={currentStage}
          latencyData={result?.latency}
          isProcessing={isProcessing}
        />
      </main>

      {/* ── BOTTOM FOOTER ───────────────────────────────────────────────────────── */}
      <footer className="w-full border-t border-hhg-border py-4 text-center text-xs text-hhg-sand-dim font-mono">
        <div className="max-w-4xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>
            <span className="font-marathi text-sm text-hhg-sand font-bold">मातृभाषा</span> &bull; Hacker House Goa 2026
          </p>
          <p className="text-[11px] text-hhg-sand-muted">
            Sarvam AI STT &bull; ChromaDB Vector &bull; BM25 RRF &bull; Groq Llama 3
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
