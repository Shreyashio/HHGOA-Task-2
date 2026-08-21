import React, { useState, useRef, useEffect } from 'react';

export default function WarliMic({ onAudioRecorded, isProcessing, disabled }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const streamRef = useRef(null);

  // Clean up audio streams and timers on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, []);

  const cleanupAudio = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    analyserRef.current = null;
    if (audioContextRef.current) {
      try {
        if (audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close().catch(() => {});
        }
      } catch (e) {}
      audioContextRef.current = null;
    }
    stopTracks();
    setAudioLevel(0);
  };

  const stopTracks = () => {
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch (e) {}
      streamRef.current = null;
    }
  };

  const startRecording = async () => {
    setErrorMsg(null);
    audioChunksRef.current = [];

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMsg("Browser does not support microphone recording. Use text input below.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Setup Web Audio API Analyser for real-time waveform pulse
      try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
          const ctx = new AudioContextClass();
          audioContextRef.current = ctx;
          const source = ctx.createMediaStreamSource(stream);
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 64;
          source.connect(analyser);
          analyserRef.current = analyser;

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const updateLevel = () => {
            if (!analyserRef.current) return;
            try {
              analyserRef.current.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
              }
              const avg = sum / dataArray.length;
              setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
              if (analyserRef.current) {
                animFrameRef.current = requestAnimationFrame(updateLevel);
              }
            } catch (e) {
              // Audio context closing safely
            }
          };
          updateLevel();
        }
      } catch (e) {
        console.warn("Web Audio Analyser not available:", e);
      }

      // Pick supported mime type
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/wav',
      ];
      let selectedMime = '';
      for (const m of mimeTypes) {
        if (MediaRecorder.isTypeSupported(m)) {
          selectedMime = m;
          break;
        }
      }

      const options = selectedMime ? { mimeType: selectedMime } : {};
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const chunks = [...audioChunksRef.current];
        const blob = new Blob(chunks, {
          type: selectedMime || 'audio/webm',
        });
        cleanupAudio();
        if (blob.size > 0 && onAudioRecorded) {
          onAudioRecorded(blob);
        }
      };

      recorder.start(100); // chunk every 100ms
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Mic access failed:", err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMsg("Microphone permission denied. Please allow microphone access in your browser settings.");
      } else {
        setErrorMsg(`Microphone error: ${err.message}`);
      }
      cleanupAudio();
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.warn("Error stopping MediaRecorder:", e);
      }
    }
    setIsRecording(false);
  };

  const cancelRecording = () => {
    audioChunksRef.current = [];
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }
    cleanupAudio();
    setIsRecording(false);
    setRecordingSeconds(0);
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="flex flex-col items-center justify-center py-5 sm:py-7 select-none">
      {/* Warli Mandala Mic Interactive Unit (HH Goa Sunrise Coral & Ocean Teal palette) */}
      <div className="relative flex items-center justify-center w-52 h-52 sm:w-60 sm:h-60">
        {/* Animated Ripple Waves when recording */}
        {isRecording && (
          <>
            <div
              className="absolute inset-0 rounded-full border border-hhg-coral/60 animate-ping opacity-30"
              style={{
                transform: `scale(${1 + audioLevel * 0.008})`,
              }}
            />
            <div className="absolute inset-2 rounded-full border-2 border-hhg-teal/40 animate-pulse opacity-40" />
            <div className="absolute -inset-4 rounded-full bg-gradient-to-r from-hhg-coral/15 via-hhg-teal/10 to-hhg-coral/15 blur-xl animate-pulse-slow" />
          </>
        )}

        {/* Geometric Warli Art SVG Ring */}
        <svg
          className={`absolute inset-0 w-full h-full pointer-events-none transition-transform duration-700 ${
            isRecording ? 'animate-spin-slow scale-105' : 'hover:rotate-45'
          }`}
          viewBox="0 0 200 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Outer dotted border */}
          <circle
            cx="100"
            cy="100"
            r="94"
            stroke="#FF6B35"
            strokeWidth="1.5"
            strokeDasharray="3 5"
            opacity={isRecording ? '0.9' : '0.35'}
          />

          {/* Warli Triangular Sunburst Pattern (24 Triangles around circumference) */}
          <g opacity={isRecording ? '1' : '0.5'}>
            {Array.from({ length: 24 }).map((_, i) => {
              const angle = (i * 360) / 24;
              const rad = (angle * Math.PI) / 180;
              const r1 = 88;
              const r2 = 94;
              const x1 = 100 + r1 * Math.cos(rad);
              const y1 = 100 + r1 * Math.sin(rad);
              const x2 = 100 + r2 * Math.cos(rad);
              const y2 = 100 + r2 * Math.sin(rad);
              return (
                <line
                  key={i}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={i % 2 === 0 ? '#FF6B35' : '#1DBFA3'}
                  strokeWidth={isRecording ? '2' : '1.5'}
                  strokeLinecap="round"
                />
              );
            })}
          </g>

          {/* Secondary Inner Concentric Ring with geometric marks */}
          <circle
            cx="100"
            cy="100"
            r="80"
            stroke="#1DBFA3"
            strokeWidth="1.2"
            strokeDasharray="6 4"
            opacity={isRecording ? '0.85' : '0.3'}
          />

          {/* Radial Warli triangle chevrons */}
          <g opacity={isRecording ? '0.9' : '0.35'}>
            {Array.from({ length: 12 }).map((_, i) => {
              const angle = (i * 360) / 12;
              return (
                <polygon
                  key={i}
                  points="100,18 97,25 103,25"
                  fill="#FFB347"
                  transform={`rotate(${angle} 100 100)`}
                />
              );
            })}
          </g>
        </svg>

        {/* Central Physical Mic Button */}
        <button
          type="button"
          disabled={disabled || isProcessing}
          onClick={isRecording ? stopRecording : startRecording}
          className={`relative z-10 w-28 h-28 sm:w-32 sm:h-32 rounded-full flex flex-col items-center justify-center transition-all duration-300 transform active:scale-95 shadow-2xl focus:outline-none ${
            isRecording
              ? 'bg-gradient-to-br from-red-600 via-hhg-coral to-hhg-coral-deep border-2 border-hhg-sand shadow-[0_0_35px_rgba(255,107,53,0.7)] scale-105'
              : isProcessing
              ? 'bg-hhg-surface border border-hhg-border opacity-75 cursor-wait'
              : 'bg-gradient-to-br from-hhg-card via-hhg-surface to-[#0B0E11] border-2 border-hhg-coral/50 hover:border-hhg-coral hover:shadow-[0_0_30px_rgba(255,107,53,0.3)]'
          }`}
          title={isRecording ? 'Click to stop and search' : 'Click to speak in English, Marathi, or Hindi'}
        >
          {isProcessing ? (
            <div key="state-processing" className="flex flex-col items-center gap-1">
              <svg className="w-7 h-7 text-hhg-coral animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-[10px] font-mono font-medium text-hhg-coral-light uppercase tracking-wider">
                Searching...
              </span>
            </div>
          ) : isRecording ? (
            <div key="state-recording" className="flex flex-col items-center">
              {/* Stop icon (square) */}
              <div className="w-6 h-6 rounded-lg bg-hhg-sand flex items-center justify-center shadow-md mb-1 animate-pulse">
                <div className="w-3 h-3 bg-[#0B0E11] rounded-sm" />
              </div>
              <span className="font-mono font-bold text-xs text-hhg-sand">
                {formatTime(recordingSeconds)}
              </span>
              <span className="text-[9px] text-hhg-sand font-mono font-semibold tracking-wider uppercase mt-0.5">
                Stop
              </span>
            </div>
          ) : (
            <div key="state-idle" className="flex flex-col items-center text-hhg-sand">
              {/* Classic Mic Icon with Sunrise Coral Accent */}
              <svg
                className="w-8 h-8 sm:w-9 sm:h-9 text-hhg-coral drop-shadow"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
              <span className="font-semibold text-xs sm:text-sm text-hhg-sand mt-1 tracking-tight">
                Click to Speak
              </span>
            </div>
          )}
        </button>
      </div>

      {/* Real-time Audio Waveform & Status Bar */}
      <div className="mt-3.5 flex flex-col items-center text-center">
        {isRecording ? (
          <div key="status-recording" className="flex flex-col items-center gap-2">
            {/* Dynamic Sound Wave Bars */}
            <div className="flex items-center gap-1 h-6">
              <div className="w-1 bg-hhg-coral rounded-full animate-wave-1" style={{ height: `${Math.max(6, audioLevel * 0.4)}px` }} />
              <div className="w-1 bg-hhg-teal rounded-full animate-wave-2" style={{ height: `${Math.max(8, audioLevel * 0.7)}px` }} />
              <div className="w-1 bg-hhg-gold rounded-full animate-wave-3" style={{ height: `${Math.max(10, audioLevel * 0.9)}px` }} />
              <div className="w-1 bg-hhg-coral rounded-full animate-wave-4" style={{ height: `${Math.max(8, audioLevel * 0.6)}px` }} />
              <div className="w-1 bg-hhg-teal rounded-full animate-wave-5" style={{ height: `${Math.max(6, audioLevel * 0.3)}px` }} />
            </div>

            <p className="text-xs sm:text-sm font-medium text-hhg-sand">
              <span className="text-hhg-coral font-semibold">Listening...</span> <span>Click the button when done speaking</span>
            </p>

            {/* Cancel Action */}
            <button
              type="button"
              onClick={cancelRecording}
              className="text-xs text-hhg-sand-muted hover:text-red-400 underline transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : isProcessing ? (
          <div key="status-processing" className="flex items-center gap-2 text-hhg-coral text-xs sm:text-sm font-medium">
            <span className="w-2 h-2 rounded-full bg-hhg-coral animate-ping" />
            <span className="font-mono">Processing audio transcription & retrieval...</span>
          </div>
        ) : (
          <div key="status-idle" className="flex flex-col items-center">
            <p className="text-xs sm:text-sm text-hhg-sand font-medium">
              <span>Ask in English, Marathi, or Hindi</span>
            </p>
            <p className="text-[11px] text-hhg-sand-muted mt-0.5 font-mono">
              <span>Sarvam AI STT &bull; ChromaDB Vector &bull; Groq Llama 3</span>
            </p>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="mt-3 px-3 py-1.5 rounded-lg bg-red-900/40 border border-red-500/40 text-red-200 text-xs flex items-center gap-2">
            <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{errorMsg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
