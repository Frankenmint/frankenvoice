import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const generateSpeech = async (
  text: string,
  seed?: number,
  filter = 'robot_radio',
) => {
  const response = await axios.post(
    `${API_BASE}/api/speech/generate`,
    { text, seed, filter_preset: filter },
    { responseType: 'blob' },
  );
  return URL.createObjectURL(response.data);
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
