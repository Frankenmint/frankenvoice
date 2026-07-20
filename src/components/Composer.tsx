import { useEffect, useState } from 'react';
import axios from 'axios';
import { CloudCog, Download, Play, RefreshCw, Sparkles } from 'lucide-react';
import {
  API_BASE,
  getCoverage,
  getProviderStatus,
  type CoverageResult,
  type ProviderStatus,
} from '../api';
import { useVoiceSettings } from '../VoiceSettingsContext';

export const Composer = () => {
  const { settings } = useVoiceSettings();
  const [text, setText] = useState(
    'Ahoy matey, FrankenVoice is broadcasting from Alibaba Cloud, assembled one fragment at a time.',
  );
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCheckingCoverage, setIsCheckingCoverage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [coverage, setCoverage] = useState<CoverageResult | null>(null);
  const [speed, setSpeed] = useState(1);
  const tokens = text.trim() ? text.trim().split(/\s+/) : [];
  const pauseScale = 0.25 + (settings.pauseLength / 100) * 2.75;

  useEffect(() => {
    let active = true;
    getProviderStatus()
      .then((status) => {
        if (active) setProviderStatus(status);
      })
      .catch(() => {
        if (active) setProviderStatus(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(
    () => () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    },
    [audioUrl],
  );

  const handleCoverage = async () => {
    if (!text.trim()) return;
    setIsCheckingCoverage(true);
    setError(null);
    try {
      setCoverage(await getCoverage(text, 3));
    } catch (coverageError) {
      console.error(coverageError);
      setError('Coverage check failed. Confirm backend is running.');
    } finally {
      setIsCheckingCoverage(false);
    }
  };

  const handleGenerate = async () => {
    if (!text.trim()) return;
    setIsGenerating(true);
    setError(null);
    try {
      const response = await axios.post(
        `${API_BASE}/api/speech/generate`,
        {
          text,
          seed: Math.floor(Math.random() * 1000000),
          filter_preset: settings.filterPreset,
          speed,
          pause_scale: pauseScale,
          variation: settings.variation,
          source_diversity: settings.sourceDiversity,
          glitch: settings.glitch,
        },
        { responseType: 'blob' },
      );
      const nextUrl = URL.createObjectURL(response.data);
      setAudioUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return nextUrl;
      });
    } catch (generationError) {
      console.error(generationError);
      setError('Generation failed. Confirm backend is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!audioUrl) return;
    const anchor = document.createElement('a');
    anchor.href = audioUrl;
    anchor.download = 'frankenvoice_export.wav';
    anchor.click();
  };

  const missingWords = coverage?.words.filter((word) => word.needed > 0) ?? [];

  return (
    <main className="flex-1 flex flex-col p-6 bg-slate-900 border-r border-slate-800">
      <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950 px-4 py-3">
        <div className="flex items-center gap-3">
          <Sparkles size={18} className="text-violet-400" />
          <div>
            <p className="text-sm font-semibold text-slate-200">One changing composite voice</p>
            <p className="text-xs text-slate-500">Qwen enriches the corpus. FrankenVoice assembles the final sentence from independent fragments.</p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400">CONTROLS ACTIVE</span>
      </div>

      <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-4 py-3">
        <div className="flex items-center gap-3">
          <CloudCog size={18} className="text-sky-400" />
          <div>
            <p className="text-sm font-semibold text-slate-300">Qwen vocabulary enrichment</p>
            <p className="text-xs text-slate-500">Transcribes sources and expands one shared word pool</p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-mono ${providerStatus?.qwen_enrichment.configured ? 'bg-sky-500/10 text-sky-400' : 'bg-amber-500/10 text-amber-400'}`}>
          {providerStatus?.qwen_enrichment.configured ? providerStatus.qwen_enrichment.asr_model : 'API KEY NEEDED'}
        </span>
      </div>

      <label className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Final line to fragment
      </label>
      <textarea
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setCoverage(null);
        }}
        className="w-full h-32 bg-slate-800 text-slate-200 p-4 rounded-lg font-mono text-lg mb-4 focus:ring-2 ring-violet-500 outline-none resize-none"
        placeholder="Enter a final line to assemble from the shared corpus..."
      />

      <div className="mb-4 flex items-center gap-4 rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400">
        <label>Rendered speed
          <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="ml-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
            {[0.75, 1, 1.25, 1.5].map((value) => <option key={value} value={value}>{value}×</option>)}
          </select>
        </label>
        <span className="font-mono text-slate-500">preset={settings.filterPreset} · variation={settings.variation} · diversity={settings.sourceDiversity} · pause={settings.pauseLength} · glitch={settings.glitch}</span>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <button onClick={handleCoverage} disabled={isCheckingCoverage || !text.trim()} className="rounded-md border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-sky-500 disabled:opacity-50">
          {isCheckingCoverage ? 'CHECKING…' : 'CHECK CORPUS COVERAGE'}
        </button>
        {coverage && <span className={`text-xs font-mono ${coverage.complete ? 'text-emerald-400' : 'text-amber-400'}`}>{coverage.complete ? `Ready: ${coverage.words.length} words covered` : `${missingWords.length} words need more variants`}</span>}
      </div>

      {coverage && missingWords.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-400">Coverage gaps</p>
          <div className="flex flex-wrap gap-2">{missingWords.map((item) => <span key={item.word} className="rounded bg-slate-900 px-2 py-1 text-xs font-mono text-slate-300">{item.word}: {item.variants}/{coverage.target_variants}</span>)}</div>
        </div>
      )}

      <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-6 overflow-y-auto">
        <p className="mb-4 text-xs uppercase tracking-wider text-slate-500">Independent word fragments</p>
        <div className="flex flex-wrap content-start gap-2">
          {tokens.map((token, index) => (
            <span key={`${token}-${index}`} className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-slate-200">
              <span className="mr-2 text-xs text-slate-500">{index + 1}</span>
              {token}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6 flex justify-between items-center">
        <div className="text-slate-500 text-sm font-mono">{tokens.length} independent fragments</div>
        <div className="flex gap-3">
          <button onClick={handleGenerate} disabled={isGenerating || !text.trim()} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-violet-900/20 transition-all disabled:opacity-50">
            {isGenerating ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />} GENERATE COMPOSITE
          </button>
          {audioUrl && <button onClick={handleDownload} className="p-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300" aria-label="Download WAV"><Download /></button>}
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {audioUrl && <div className="mt-4 bg-slate-800 p-2 rounded-lg"><audio controls src={audioUrl} className="w-full" autoPlay /></div>}
    </main>
  );
};