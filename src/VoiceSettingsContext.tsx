import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { defaultVoiceSettings, type VoiceSettings } from './voiceSettings';

interface VoiceSettingsContextValue {
  settings: VoiceSettings;
  setSetting: <K extends keyof VoiceSettings>(key: K, value: VoiceSettings[K]) => void;
  resetSettings: () => void;
}

const VoiceSettingsContext = createContext<VoiceSettingsContextValue | null>(null);

export const VoiceSettingsProvider = ({ children }: { children: ReactNode }) => {
  const [settings, setSettings] = useState<VoiceSettings>(defaultVoiceSettings);

  const value = useMemo<VoiceSettingsContext