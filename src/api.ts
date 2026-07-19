import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type GenerationProvider = 'qwen_cloud' | 'local';
export type ProviderPreference = 'auto' | 'qwen_cloud' | 'local';

export interface GeneratedSpeech {
  url: string;
  provider: GenerationProvider;
  fallbackReason?: string;
}

export interface ProviderStatus {
  default: ProviderPreference;
  strategy: string;
  qwen_cloud: {
    configured: boolean;
    model: string;
    voice: string;
    endpoint: string;
  };
  local: {
    available: boolean;
  };
}

export const generateSpeech = async (
  text: string,
  seed?: number,
  filter = 'robot_radio',
  provider: ProviderPreference = 'auto',
): Promise<GeneratedSpeech> => {
  const response = await axios.post(
    `${API_BASE}/api/speech/generate`,
    { text, seed, filter_preset: filter, provider },
    { responseType: 'blob' },
  );
  const providerHeader = response.headers['x-frankenvoice-provider'];
  return {
    url: URL.createObjectURL(response.data),
    provider: providerHeader === 'qwen_cloud' ? 'qwen_cloud' : 'local',
    fallbackReason: response.headers['x-frankenvoice-fallback'] || undefined,
  };
};

export const getProviderStatus = async (): Promise<ProviderStatus> => {
  const response = await axios.get(`${API_BASE}/api/providers/status`);
  return response.data;
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
