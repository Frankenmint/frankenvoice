import { useEffect, useState } from 'react';
import { CloudCog, Download, Play, RefreshCw, Sparkles } from 'lucide-react';
import {
  generateSpeech,
  getCoverage,
  getProviderStatus,
  type CoverageResult,
  type ProviderStatus,
} from '../api';
import { WordBlock } from './WordBlock';

const filters = ['robot_radio', 'clean', 'telephone', 'damaged_tape'] as const;

export const Composer = () => {
  const [text, setText] = useState(
    'Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo.',
  );
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCheckingCoverage, setIsCheckingCoverage] = useState(false);
  const [lockedWords, setLockedWords] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [coverage, setCoverage] = useState<CoverageResult | null>(null);
  const [filter, setFilter] = useState<(typeof filters)[number]>('robot_radio');
  const [speed, setSpeed] = useState(1);
  const [pauseScale, setPauseScale] = useState(1);
  const tokens = text.trim() ? text.trim().split(/\s+/) : [];

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
      const generated = await generateSpeech(
        text,
        Math.floor(Math.random() * 1000),
        filter,
        speed,
        pauseScale,
      );
      setAudioUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return generated.url;
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
            <p className="text-xs text-slate-500">Every output word is independently selected from the shared corpus</p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400">BUMBLEBEE MODE</span>
      </div>

      <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-4 py-3">
        <div className="flex items-center gap-3">
          <CloudCog size={18} className="text-sky-400" />
          <div>
            <p className="text-sm font-semibold text-slate-300">Qwen vocabulary enrichment</p>
            <p className="text-xs text-slate-500">Transcribes sources and expands one global word pool</p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-mono ${providerStatus?.qwen_enrichment.configured ? 'bg-sky-500/10 text-sky-400' : 'bg-amber-500/10 text-amber-400'}`}>
          {providerStatus?.qwen_enrichment.configured ? providerStatus.qwen_enrichment.asr_model : 'API KEY NEEDED'}
        </span>
      </div>

      <textarea
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setCoverage(null);
        }}
        className="w-full h-32 bg-slate-800 text-slate-200 p-4 rounded-lg font-mono text-lg mb-4 focus:ring-2 ring-violet-500 outline-none resize-none"
        placeholder="Enter text to fragment..."
      />

      <div className="mb-4 grid grid-cols-3 gap-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
        <label className="text-xs text-slate-500">Filter
          <select value={filter} onChange={(event) => setFilter(event.target.value as (typeof filters)[number])} className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-2 text-slate-300">
            {filters.map((item) => <option key={item} value={item}>{item.replace('_', ' ')}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-500">Rendered speed
          <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-2 text-slate-300">
            {[0.75, 1, 1.25, 1.5].map((value) => <option key={value} value={value}>{value}×</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-500">Punctuation pauses
          <select value={pauseScale} onChange={(event) => setPauseScale(Number(event.target.value))} className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-2 text-slate-300">
            <option value={0.6}>Tight</option><option value={1}>Normal</option><option value={1.5}>Dramatic</option>
          </select>
        </label>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <button onClick={handleCoverage} disabled={isCheckingCoverage || !text.trim()} className="rounded-md border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-sky-500 disabled:opacity-50">
          {isCheckingCoverage ? 'CHECKING…' : 'CHECK DATASET COVERAGE'}
        </button>
        {coverage && <span className={`text-xs font-mono ${coverage.complete ? 'text-emerald-400' : 'text-amber-400'}`}>{coverage.complete ? `Ready: ${coverage.words.length} words covered` : `${missingWords.length} words need more variants`}</span>}
      </div>

      {coverage && missingWords.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-400">Coverage gaps</p>
          <div className="flex flex-wrap gap-2">{missingWords.map((item) => <span key={item.word} className="rounded bg-slate-900 px-2 py-1 text-xs font-mono text-slate-300">{item.word}: {item.variants}/{coverage.target_variants}</span>)}</div>
          <p className="mt-2 text-xs text-slate-500">Paste these words into Global vocabulary enrichment in the Sources panel.</p>
        </div>
      )}

      <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-6 overflow-y-auto flex flex-wrap content-start gap-y-4">
        {tokens.map((token, index) => (
          <WordBlock key={`${token}-${index}`} word={token} index={index} onReroll={(wordIndex) => console.log('Reroll', wordIndex)} onPlay={(word) => console.log('Preview', word)} isLocked={lockedWords.includes(index)} onToggleLock={(wordIndex) => setLockedWords((current) => current.includes(wordIndex) ? current.filter((item) => item !== wordIndex) : [...current, wordIndex])} />
        ))}
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
