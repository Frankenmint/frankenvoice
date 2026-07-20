import { RotateCcw } from 'lucide-react';
import { useVoiceSettings } from '../VoiceSettingsContext';
import {
  filterPresets,
  presetSettings,
  type FilterPreset,
  type VoiceSettings,
} from '../voiceSettings';

const presetLabels: Record<FilterPreset, string> = {
  robot_radio: 'Robot Radio',
  clean: 'Clean',
  telephone: 'Telephone',
  damaged_tape: 'Damaged Tape',
};

const sliders: Array<{
  key: keyof Pick<VoiceSettings, 'variation' | 'sourceDiversity' | 'pauseLength' | 'glitch'>;
  label: string;
  help: string;
}> = [
  { key: 'variation', label: 'Variation', help: 'How widely FrankenVoice samples from available real clips.' },
  { key: 'sourceDiversity', label: 'Source diversity', help: 'How strongly consecutive words avoid the same recording source.' },
  { key: 'pauseLength', label: 'Pause length', help: 'Scales the pauses inserted between fragments.' },
  { key: 'glitch', label: 'Glitch', help: 'Adds stutters and dropouts after the composite is assembled.' },
];

export const VoiceControls = () => {
  const { settings, setSetting, resetSettings } = useVoiceSettings();

  const applyPreset = (preset: FilterPreset) => {
    const next = presetSettings[preset];
    setSetting('filterPreset', next.filterPreset);
    setSetting('variation', next.variation);
    setSetting('sourceDiversity', next.sourceDiversity);
    setSetting('pauseLength', next.pauseLength);
    setSetting('glitch', next.glitch);
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-bold tracking-wide text-slate-100">COMPOSER SOUND</h2>
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
        <p className="mt-1 text-xs leading-5 text-emerald-400">
          Applied when you click Generate Composite. These controls do not change imported recordings.
        </p>
      </div>

      <label className="block text-sm">
        <span className="mb-2 block text-slate-400">Preset</span>
        <select
          value={settings.filterPreset}
          onChange={(event) => applyPreset(event.target.value as FilterPreset)}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
        >
          {filterPresets.map((preset) => (
            <option key={preset} value={preset}>{presetLabels[preset]}</option>
          ))}
        </select>
        <span className="mt-2 block text-xs text-slate-500">
          Choosing a preset updates all sliders below. You can then fine-tune them.
        </span>
      </label>

      {sliders.map(({ key, label, help }) => (
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
          <span className="mt-1 block text-xs leading-4 text-slate-600">{help}</span>
        </label>
      ))}
    </div>
  );
};
