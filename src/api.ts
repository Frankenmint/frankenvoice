import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export const generateSpeech = async (text: string, seed?: number, filter: string = 'robot_radio') => {
  const response = await axios.post(`${API_BASE}/api/speech/generate`, 
    { text, seed, filter_preset: filter },
    { responseType: 'blob' }
  );
  return URL.createObjectURL(response.data);
};

export const getWordVariants = async (word: string) => {
  const response = await axios.get(`${API_BASE}/api/words/${word}`);
  return response.data;
};
