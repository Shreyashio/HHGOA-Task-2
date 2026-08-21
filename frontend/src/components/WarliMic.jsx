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
      setErrorMsg("Browser does not support audio recording.");
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
            } catch (e) {}
          };
          updateLevel();
        }
      } catch (e) {}

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

      recorder.start(100);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Mic access failed:", err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMsg("Microphone permission denied. Please allow microphone access.");
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
      } catch (e) {}
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
    <div className="flex flex-col items-center justify-center select-none pt-2 pb-1">
      {/* Soft Breathing Single-Ring Mic Unit (No busy radar / dashes / triangles) */}
      <div className="relative flex items-center justify-center w-36 h-36 sm:w-40 sm:h-40">
        {/* The single organic breathing ring */}
        <div
          className={`absolute inset-0 rounded-full transition-all duration-500 pointer-events-none ${
            isRecording
              ? 'bg-[#FF6B35]/20 border border-[#FF6B35]/70 animate-breathe-active shadow-[0_0_30px_rgba(255,107,53,0.35)]'
              : 'border border-[#FF6B35]/25 animate-breathe shadow-[0_0_20px_rgba(255,107,53,0.15)]'
          }`}
          style={{
            transform: isRecording ? `scale(${1.08 + audioLevel * 0.003})` : undefined,
          }}
        />

        {/* Central Physical Tactile Mic Button */}
        <button
          type="button"
          disabled={disabled || isProcessing}
          onClick={isRecording ? stopRecording : startRecording}
          className={`relative z-10 w-24 h-24 sm:w-28 sm:h-28 rounded-full flex flex-col items-center justify-center transition-all duration-300 transform active:scale-95 focus:outline-none ${
            isRecording
              ? 'bg-[#FF6B35] text-[#0B0E11] shadow-[0_0_30px_rgba(255,107,53,0.5)] scale-105'
              : isProcessing
              ? 'bg-[#161B22] border border-white/[0.08] opacity-75 cursor-wait'
              : 'bg-[#161B22] hover:bg-[#1C222B] text-[#F5F0E6] border border-white/[0.12] hover:border-[#FF6B35]/60 hover:shadow-[0_0_20px_rgba(255,107,53,0.2)]'
          }`}
          title={isRecording ? 'Click to stop' : 'Click to speak'}
        >
          {isProcessing ? (
            <div key="state-processing" className="flex flex-col items-center gap-1.5">
              <svg className="w-5 h-5 text-[#FF6B35] animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-[11px] font-medium text-[#8A8F94]">
                Thinking...
              </span>
            </div>
          ) : isRecording ? (
            <div key="state-recording" className="flex flex-col items-center text-[#0B0E11]">
              <div className="w-4 h-4 bg-[#0B0E11] rounded-sm mb-1" />
              <span className="font-medium text-xs">
                {formatTime(recordingSeconds)}
              </span>
              <span className="text-[10px] font-semibold tracking-wide uppercase mt-0.5">
                Stop
              </span>
            </div>
          ) : (
            <div key="state-idle" className="flex flex-col items-center text-[#F5F0E6]">
              <svg
                className="w-7 h-7 text-[#FF6B35]"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
              <span className="text-xs font-medium text-[#8A8F94] mt-1">
                Speak
              </span>
            </div>
          )}
        </button>
      </div>

      {/* Recording State & Subtle Waveform */}
      {isRecording && (
        <div key="status-recording" className="mt-2.5 flex flex-col items-center gap-1.5 animate-fadeIn">
          <div className="flex items-center gap-1 h-5">
            <div className="w-1 bg-[#FF6B35] rounded-full animate-qwave-1" />
            <div className="w-1 bg-[#FF6B35] rounded-full animate-qwave-2" />
            <div className="w-1 bg-[#FF6B35] rounded-full animate-qwave-3" />
            <div className="w-1 bg-[#FF6B35] rounded-full animate-qwave-4" />
            <div className="w-1 bg-[#FF6B35] rounded-full animate-qwave-5" />
          </div>

          <button
            type="button"
            onClick={cancelRecording}
            className="text-xs text-[#8A8F94] hover:text-red-400 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="mt-2 px-3 py-1.5 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
