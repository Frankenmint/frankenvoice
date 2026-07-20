import type { VoiceSettings } from '../voiceSettings';

const presets: Array<{ value: VoiceSettings['filterPreset']; label: string }> = [
  { value: 'robot_radio', label: 'Robot Radio' },
  { value: 'clean', label: 'Clean' },
  { value: 'telephone', label: 'Telephone' },
  { value: 'damaged_tape', label: 'Damaged Tape' },
];

interface VoiceControlsProps {
  settings: VoiceSettings;
  onChange: (settings: VoiceSettings) => void;
}

export const VoiceControls = ({ settings, onChange }: VoiceControlsProps) => {
  const set = <K extends keyof VoiceSettings>(key: K, value: VoiceSettings[K]) => {
    onChange({ ...settings, [key]: value });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-bold tracking-wide text-slate-100">VOICE CONTROLS</h2>
        <p className="mt-1 text-xs text-slate-500">Applied to Composer and Reader output</p>
      </div>

      <label className="block text-sm">
        <span className="mb-2 block text-slate-400">Preset</span>
        <select
          value={settings.filterPreset}
          onChange={(event) => set('filterPreset', event.target.value as VoiceSettings['filterPreset'])}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
        >
          {presets.map((preset) => (
            <option key={preset.value} value={preset.value}>{preset.label}</option>
          ))}
        </select>
      </label>

      <label className="block text-sm">
        <span className="mb-2 flex justify-between text-slate-400">
          Pause length
          <span className="font-mono text-slate-300">{settings.pauseLength}</span>
        </span>
        <input
          type="range"
          min="0"
          max="100"
          value={settings.pauseLength}
          onChange={(event) => set('pauseLength', Number(event.target.value))}
          className="w-full"
        />
      </label>

      {([
        ['Variation', 'variation'],
        ['Source diversity', 'sourceDiversity'],
        ['Glitch', 'glitch'],
      ] as const).map(([label, key]) => (
        <label key={key} className="block text-sm opacity-55">
          <span className="mb-2 flex justify-between text-slate-400">
            <span>{label} <span className="text-[10px] uppercase text-slate-600">not wired yet</span></span>
            <span className="font-mono text-slate-500">{settings[key]}</span>
          </span>
          <input type="range" min="0" max="100" value={settings[key]} disabled className="w-full" />
        </label>
      ))}
    </div>
  );
};
