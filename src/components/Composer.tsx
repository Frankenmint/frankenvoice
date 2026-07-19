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
        'robot_radio',
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
            <p className="text-sm font-semibold text-slate-200">Composite speech only</p>
            <p className="text-xs text-slate-500">
              Every output word is selected as an independent fragment
            </p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400">
          BUMBLEBEE MODE
        </span>
      </div>

      <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-4 py-3">
        <div className="flex items-center gap-3">
          <CloudCog size={18} className="text-sky-400" />
          <div>
            <p className="text-sm font-semibold text-slate-300">Qwen dataset enrichment</p>
            <p className="text-xs text-slate-500">
              Transcribes sources and generates missing single-word variants
            </p>
          </div>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-mono ${
            providerStatus?.qwen_enrichment.configured
              ? 'bg-sky-500/10 text-sky-400'
              : 'bg-amber-500/10 text-amber-400'
          }`}
        >
          {providerStatus?.qwen_enrichment.configured
            ? providerStatus.qwen_enrichment.asr_model
            : 'API KEY NEEDED'}
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

      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={handleCoverage}
          disabled={isCheckingCoverage || !text.trim()}
          className="rounded-md border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-sky-500 disabled:opacity-50"
        >
          {isCheckingCoverage ? 'CHECKING…' : 'CHECK DATASET COVERAGE'}
        </button>
        {coverage && (
          <span className={`text-xs font-mono ${coverage.complete ? 'text-emerald-400' : 'text-amber-400'}`}>
            {coverage.complete
              ? `Ready: ${coverage.words.length} words covered`
              : `${missingWords.length} words need more variants`}
          </span>
        )}
      </div>

      {coverage && missingWords.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-400">
            Coverage gaps
          </p>
          <div className="flex flex-wrap gap-2">
            {missingWords.map((item) => (
              <span key={item.word} className="rounded bg-slate-900 px-2 py-1 text-xs font-mono text-slate-300">
                {item.word}: {item.variants}/{coverage.target_variants}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Use a source voice profile in the Sources panel, then run Qwen enrichment to create only these missing word clips.
          </p>
        </div>
      )}

      <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-6 overflow-y-auto flex flex-wrap content-start gap-y-4">
        {tokens.map((token, index) => (
          <WordBlock
            key={`${token}-${index}`}
            word={token}
            index={index}
            onReroll={(wordIndex) => console.log('Reroll', wordIndex)}
            onPlay={(word) => console.log('Preview', word)}
            isLocked={lockedWords.includes(index)}
            onToggleLock={(wordIndex) => {
              setLockedWords((current) =>
                current.includes(wordIndex)
                  ? current.filter((item) => item !== wordIndex)
                  : [...current, wordIndex],
              );
            }}
          />
        ))}
      </div>

      <div className="mt-6 flex justify-between items-center">
        <div className="text-slate-500 text-sm font-mono">{tokens.length} independent fragments</div>
        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !text.trim()}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-violet-900/20 transition-all disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />}
            GENERATE COMPOSITE
          </button>

          {audioUrl && (
            <button
              onClick={handleDownload}
              className="p-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300"
              aria-label="Download WAV"
            >
              <Download />
            </button>
          )}
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {audioUrl && (
        <div className="mt-4 bg-slate-800 p-2 rounded-lg">
          <audio controls src={audioUrl} className="w-full" autoPlay />
        </div>
      )}
    </main>
  );
};
