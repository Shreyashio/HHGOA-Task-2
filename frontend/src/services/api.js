/**
 * api.js — Frontend API client for Voice-RAG (MATRUBHASHA)
 * 
 * When served via FastAPI on port 8000: API_BASE = '' (same origin)
 * When served via Vite dev: API_BASE = 'http://127.0.0.1:8000' (cross-origin, handled by proxy or explicit)
 */

// If VITE_API_URL is set (e.g. in .env.local), use it. Otherwise auto-detect.
// In production (served from FastAPI), requests go to same origin (port 8000).
// In Vite dev mode with proxy, empty string works too.
const API_BASE = import.meta.env.VITE_API_URL ?? '';

export const MOCK_RESPONSES = [
  {
    query: "प्रकाशसंश्लेषण म्हणजे काय?",
    transcript: "प्रकाशसंश्लेषण म्हणजे काय?",
    language_detected: "mr",
    answer: "प्रकाशसंश्लेषण (Photosynthesis) ही वनस्पती, शेवाळ आणि काही जीवाणूंद्वारे सूर्यप्रकाशाची ऊर्जा वापरून रासायनिक ऊर्जा निर्माण करण्याची नैसर्गिक प्रक्रिया आहे. या प्रक्रियेत हरितद्रव्याच्या (Chlorophyll) सहाय्याने पाणी आणि कार्बन डायऑक्साईडचे ग्लुकोज आणि ऑक्सिजनमध्ये रूपांतर होते.",
    grounded: true,
    confidence: 0.96,
    guardrail_passed: true,
    model: "llama-3.1-8b-instant (Groq) [DEMO]",
    sources: [
      {
        source_index: 0,
        doc_id: "MSMARCO_MR_7482",
        chunk_id: "chk_mr_001",
        lang: "mr",
        score: 0.942,
        snippet: "प्रकाशसंश्लेषण ही अशी जैविक प्रक्रिया आहे ज्यामध्ये हिरव्या वनस्पती सूर्यप्रकाशातील ऊर्जा शोषून घेतात आणि तिचे रूपांतर रासायनिक ऊर्जेत करतात. ऑक्सिजन हा या प्रक्रियेचा मुख्य उपउत्पादन आहे."
      },
      {
        source_index: 1,
        doc_id: "MSMARCO_MR_7483",
        chunk_id: "chk_mr_002",
        lang: "mr",
        score: 0.887,
        snippet: "हरितद्रव्य (Chlorophyll) सूर्यप्रकाशातील निळे आणि लाल किरण शोषून ग्लुकोजची निर्मिती करते. ही प्रक्रिया पृथ्वीवरील जीवसृष्टीचा मुख्य आधार आहे."
      }
    ],
    latency: {
      input_validation_ms: 1.2,
      stt_ms: 320.5,
      input_guardrail_ms: 3.4,
      retrieval_ms: 48.2,
      reranking_ms: 24.1,
      context_validation_ms: 2.1,
      generation_ms: 280.6,
      grounding_check_ms: 12.3,
      search_pipeline_ms: 72.3,
      total_ms: 692.4,
    }
  },
  {
    query: "who was the first president of India",
    transcript: "who was the first president of India",
    language_detected: "en",
    answer: "Dr. Rajendra Prasad was the first President of independent India, serving from 1950 to 1962. He was an Indian independence activist, lawyer, and scholar who also served as the president of the Constituent Assembly that drafted the Constitution of India.",
    grounded: true,
    confidence: 0.98,
    guardrail_passed: true,
    model: "llama-3.1-8b-instant (Groq) [DEMO]",
    sources: [
      {
        source_index: 0,
        doc_id: "MSMARCO_EN_10921",
        chunk_id: "chk_en_102",
        lang: "en",
        score: 0.958,
        snippet: "Dr. Rajendra Prasad (3 December 1884 – 28 February 1963) was an Indian independence activist, lawyer, scholar and subsequently the first President of India, in office from 1950 to 1962."
      },
      {
        source_index: 1,
        doc_id: "MSMARCO_EN_10922",
        chunk_id: "chk_en_103",
        lang: "en",
        score: 0.891,
        snippet: "Upon the Republic Day in 1950, Dr. Rajendra Prasad was elected as the first President of India by the Constituent Assembly."
      }
    ],
    latency: {
      input_validation_ms: 0.9,
      stt_ms: 290.4,
      input_guardrail_ms: 2.8,
      retrieval_ms: 42.1,
      reranking_ms: 18.7,
      context_validation_ms: 1.5,
      generation_ms: 245.2,
      grounding_check_ms: 9.8,
      search_pipeline_ms: 60.8,
      total_ms: 611.4,
    }
  }
];

/**
 * Check backend health. Returns { online: boolean, data?, error? }
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(4000),
      cache: 'no-store',
    });
    if (res.ok) {
      const data = await res.json();
      return { online: true, data };
    }
    return { online: false, error: `HTTP ${res.status}` };
  } catch (err) {
    return { online: false, error: err.message };
  }
}

/**
 * Submit an audio blob to the /ask-voice endpoint.
 */
export async function queryVoice({ audioBlob, strategy = 'sentence', lang = null, mock = false, onProgress = null }) {
  if (mock) {
    await simulateProgress(onProgress, false);
    const mockItem = MOCK_RESPONSES[0];
    return { ...mockItem, mock: true };
  }

  const formData = new FormData();
  const filename = audioBlob.type?.includes('wav') ? 'recording.wav' : 'recording.webm';
  formData.append('audio', audioBlob, filename);
  if (strategy) formData.append('strategy', strategy);
  if (lang) formData.append('lang', lang);
  formData.append('mock', 'false');

  if (onProgress) onProgress('stt');

  const res = await fetch(`${API_BASE}/ask-voice`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
    } catch { /* ignore */ }
    throw new Error(errorMsg);
  }

  if (onProgress) onProgress('answer');
  return await res.json();
}

/**
 * Submit a text query to the /ask-text endpoint.
 */
export async function queryText({ query, strategy = 'sentence', langFilter = null, mock = false, onProgress = null }) {
  if (mock) {
    await simulateProgress(onProgress, true);
    const matched = MOCK_RESPONSES.find(m =>
      query.toLowerCase().split(' ').some(w => m.query.toLowerCase().includes(w))
    ) || MOCK_RESPONSES[0];
    return { ...matched, query, transcript: query, mock: true };
  }

  if (onProgress) onProgress('retrieve');

  const res = await fetch(`${API_BASE}/ask-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      strategy,
      lang_filter: langFilter,
      mock: false,
    }),
  });

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
    } catch { /* ignore */ }
    throw new Error(errorMsg);
  }

  if (onProgress) onProgress('answer');
  return await res.json();
}

async function simulateProgress(onProgress, isText = false) {
  if (!onProgress) return;
  if (!isText) {
    onProgress('stt');
    await new Promise(r => setTimeout(r, 350));
  }
  onProgress('retrieve');
  await new Promise(r => setTimeout(r, 120));
  onProgress('rerank');
  await new Promise(r => setTimeout(r, 90));
  onProgress('generate');
  await new Promise(r => setTimeout(r, 380));
  onProgress('answer');
}
