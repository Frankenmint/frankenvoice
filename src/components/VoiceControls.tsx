import { RotateCcw } from 'lucide-react';
import { useVoiceSettings } from '../VoiceSettingsContext';
import { filterPresets, type FilterPreset, type VoiceSettings } from '../voiceSettings';

const presetLabels: Record<FilterPreset, string> = {
  robot_radio: 'Robot Radio',
  clean: 'Clean',
  telephone: 'Telephone',
  damaged_tape: 'Damaged Tape',
};

const sliders: Array<{ key: keyof Pick<VoiceSettings, 'variation' | 'sourceDiversity' | 'pauseLength' | 'glitch'>; label: string }> = [
  { key: 'variation', label: 'Variation' },
  { key: 'sourceDiversity', label: 'Source diversity' },
  { key: 'pauseLength', label: 'Pause length' },
  { key: 'glitch', label: 'Glitch' },
];

export const VoiceControls = () => {
  const { settings, setSetting, resetSettings } = useVoiceSettings();

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-bold tracking-wide text-slate-100">VOICE CONTROLS</h2>
          <button
            type="button"
            onClick={resetSettings}
            className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-200"
            aria-label="Reset voice controls"
            title="Reset voice controls"
          >
            <RotateCcw size={15} />
          </button>
        </div>
        <p className="mt-1 text-xs text-emerald-400">Applied to generated FrankenVoice audio</p>
      </div>

      <label className="block text-sm">
        <span className="mb-2 block text-slate-400">Preset</span>
        <select
          value={settings.filterPreset}
          onChange={(event) => setSetting('filterPreset', event.target.value as FilterPreset)}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
        >
          {filterPresets.map((preset) => (
            <option key={preset} value={preset}>{presetLabels[preset]}</option>
          ))}
        </select>
      </label>

      {sliders.map(({ key, label }) => (
        <label key={key} className="block text-sm">
          <span className="mb-2 flex justify-between text-slate-400">
            <span>{label}</span>
            <span className="font-mono text-slate-300">{settings[key]}</span>
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={settings[key]}
            onChange={(event) => setSetting(key, Number(event.target.value))}
            className="w-full"
          />
        </label>
      ))}
    </div>
  );
};
