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

  const value = useMemo<VoiceSettingsContextValue>(
    () => ({
      settings,
      setSetting: (key, nextValue) => {
        setSettings((current) => ({ ...current, [key]: nextValue }));
      },
      resetSettings: () => setSettings(defaultVoiceSettings),
    }),
    [settings],
  );

  return <VoiceSettingsContext.Provider value={value}>{children}</VoiceSettingsContext.Provider>;
};

export const useVoiceSettings = () => {
  const context = useContext(VoiceSettingsContext);
  if (!context) throw new Error('useVoiceSettings must be used inside VoiceSettingsProvider');
  return context;
};
