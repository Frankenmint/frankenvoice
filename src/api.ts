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
