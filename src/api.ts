import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface GeneratedSpeech {
  url: string;
  provider: 'composite';
}

export interface ProviderStatus {
  speech_strategy: 'composite_only';
  final_speech: {
    provider: string;
    whole_sentence_cloud_tts: false;
    voice_count: 1;
  };
  qwen_enrichment: {
    configured: boolean;
    asr_model: string;
    tts_model: string;
    voices: string[];
    strategy: string;
  };
}

export interface CoverageWord {
  word: string;
  variants: number;
  needed: number;
}

export interface CoverageResult {
  target_variants: number;
  complete: boolean;
  words: CoverageWord[];
}

export interface ConversationChunks {
  cleaned_text: string;
  chunks: string[];
  count: number;
}

export interface SourceProgress {
  id: number;
  title: string;
  source_type: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  clip_count: number;
  created_at: string;
}

export interface AutopilotRun {
  id: string;
  status: 'awaiting_approval' | 'approved' | 'executing' | 'complete' | 'failed';
  goal: string;
  target_text: string;
  source_urls: string[];
  coverage_before: CoverageResult;
  plan: {
    summary: string;
    rationale: string;
    steps: string[];
    target_variants: number;
    estimated_external_actions: number;
  };
  approval: null | {
    allow_source_imports: boolean;
    allow_cloud_enrichment: boolean;
  };
  events: Array<{ type: string; message: string; tool?: string }>;
  result: null | {
    report: string;
    audio_ready: boolean;
    coverage_final: CoverageResult;
  };
  error: string | null;
}

export const generateSpeech = async (
  text: string,
  seed?: number,
  filter = 'robot_radio',
  speed = 1,
  pauseScale = 1,
  signal?: AbortSignal,
): Promise<GeneratedSpeech> => {
  const response = await axios.post(
    `${API_BASE}/api/speech/generate`,
    { text, seed, filter_preset: filter, speed, pause_scale: pauseScale },
    { responseType: 'blob', signal },
  );
  return {
    url: URL.createObjectURL(response.data),
    provider: 'composite',
  };
};

export const getProviderStatus = async (): Promise<ProviderStatus> => {
  const response = await axios.get(`${API_BASE}/api/providers/status`);
  return response.data;
};

export const getCoverage = async (
  text: string,
  targetVariants = 3,
): Promise<CoverageResult> => {
  const response = await axios.post(`${API_BASE}/api/dataset/coverage`, {
    text,
    target_variants: targetVariants,
  });
  return response.data;
};

export const enrichDataset = async (text: string, targetVariants = 3) => {
  const response = await axios.post(`${API_BASE}/api/dataset/enrich`, {
    text,
    target_variants: targetVariants,
  });
  return response.data as {
    source_id: number;
    corpus: string;
    created: Array<{ word: string; clip_id: number; voice: string }>;
    failures: Array<{ word: string; reason: string }>;
  };
};

export const prepareConversation = async (
  text: string,
  maxCharacters = 420,
  skipCodeBlocks = true,
): Promise<ConversationChunks> => {
  const response = await axios.post(`${API_BASE}/api/conversation/chunks`, {
    text,
    max_characters: maxCharacters,
    skip_code_blocks: skipCodeBlocks,
  });
  return response.data;
};

export const createAutopilotPlan = async (
  goal: string,
  targetText: string,
  sourceUrls: string[],
  targetVariants = 3,
): Promise<AutopilotRun> => {
  const response = await axios.post(`${API_BASE}/api/autopilot/plan`, {
    goal,
    target_text: targetText,
    source_urls: sourceUrls,
    target_variants: targetVariants,
  });
  return response.data;
};

export const getAutopilotRun = async (runId: string): Promise<AutopilotRun> => {
  const response = await axios.get(`${API_BASE}/api/autopilot/runs/${runId}`);
  return response.data;
};

export const approveAutopilotRun = async (
  runId: string,
  allowSourceImports: boolean,
  allowCloudEnrichment: boolean,
): Promise<AutopilotRun> => {
  const response = await axios.post(`${API_BASE}/api/autopilot/runs/${runId}/approve`, {
    allow_source_imports: allowSourceImports,
    allow_cloud_enrichment: allowCloudEnrichment,
  });
  return response.data;
};

export const autopilotAudioUrl = (runId: string) =>
  `${API_BASE}/api/autopilot/runs/${runId}/audio`;

export const transcribeSourceWithQwen = async (sourceId: number, audioUrl: string) => {
  const response = await axios.post(`${API_BASE}/api/sources/${sourceId}/qwen-transcribe`, {
    audio_url: audioUrl,
  });
  return response.data as {
    source_id: number;
    provider: 'qwen_asr';
    created: Array<{ word: string; clip_id: number }>;
  };
};

export const getWordVariants = async (word: string) => {
  const response = await axios.get(`${API_BASE}/api/words/${encodeURIComponent(word)}`);
  return response.data;
};

export const importYouTubeSource = async (url: string) => {
  const response = await axios.post(`${API_BASE}/api/sources/youtube`, null, {
    params: { url },
  });
  return response.data as { status: string; source_id: number };
};

export const getSourceProgress = async (sourceId: number): Promise<SourceProgress> => {
  const response = await axios.get(`${API_BASE}/api/sources/${sourceId}`);
  return response.data;
};
