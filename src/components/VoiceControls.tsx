const presets = ['Robot Radio', 'Clean', 'Telephone', 'Damaged Tape'];

export const VoiceControls = () => (
  <div className="space-y-6">
    <div>
      <h2 className="font-bold tracking-wide text-slate-100">VOICE CONTROLS</h2>
      <p className="mt-1 text-xs text-slate-500">Shared transmission filter</p>
    </div>

    <label className="block text-sm">
      <span className="mb-2 block text-slate-400">Preset</span>
      <select className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2">
        {presets.map((preset) => (
          <option key={preset}>{preset}</option>
        ))}
      </select>
    </label>

    {['Variation', 'Source diversity', 'Pause length', 'Glitch'].map((label) => (
      <label key={label} className="block text-sm">
        <span className="mb-2 flex justify-between text-slate-400">
          {label}
          <span className="font-mono text-slate-600">50</span>
        </span>
        <input type="range" min="0" max="100" defaultValue="50" className="w-full" />
      </label>
    ))}
  </div>
);
