import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { VoiceSettingsProvider } from './VoiceSettingsContext';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <VoiceSettingsProvider>
      <App />
    </VoiceSettingsProvider>
  </React.StrictMode>,
);
