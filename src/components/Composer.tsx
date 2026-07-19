import { useEffect, useState } from 'react';
import { Cloud, Cpu, Download, Play, RefreshCw } from 'lucide-react';
import {
  generateSpeech,
  getProviderStatus,
  type GenerationProvider,
  type ProviderStatus,
} from '../api';
import { WordBlock } from './WordBlock';

export const Composer = () => {
  const [text, setText] = useState(
    'Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo.',
  );
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lockedWords, setLockedWords] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [providerUsed, setProviderUsed] = useState<GenerationProvider | null>(null);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
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

  const handleGenerate = async () => {
    if (!text.trim()) return;
    setIsGenerating(true);
    setError(null);
    setFallbackReason(null);
    try {
      const generated = await generateSpeech(
        text,
        Math.floor(Math.random() * 1000),
        'robot_radio',
        'auto',
      );
      setAudioUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return generated.url;
      });
      setProviderUsed(generated.provider);
      setFallbackReason(generated.fallbackReason ?? null);
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

  return (
    <main className="flex-1 flex flex-col p-6 bg-slate-900 border-r border-slate-800">
      <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950 px-4 py-3">
        <div className="flex items-center gap-3">
          <Cloud size={18} className="text-violet-400" />
          <div>
            <p className="text-sm font-semibold text-slate-200">Qwen Cloud first</p>
            <p className="text-xs text-slate-500">Automatic local fragment fallback</p>
          </div>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-mono ${
            providerStatus?.qwen_cloud.configured
              ? 'bg-emerald-500/10 text-emerald-400'
              : 'bg-amber-500/10 text-amber-400'
          }`}
        >
          {providerStatus?.qwen_cloud.configured
            ? providerStatus.qwen_cloud.model
            : 'API KEY NEEDED'}
        </span>
      </div>

      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="w-full h-32 bg-slate-800 text-slate-200 p-4 rounded-lg font-mono text-lg mb-6 focus:ring-2 ring-violet-500 outline-none resize-none"
        placeholder="Enter text to fragment..."
      />

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
        <div className="text-slate-500 text-sm font-mono">{tokens.length} fragments ready</div>
        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !text.trim()}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-violet-900/20 transition-all disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />}
            GENERATE TRANSMISSION
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

      {providerUsed && (
        <div className="mt-3 flex items-center gap-2 text-xs font-mono">
          {providerUsed === 'qwen_cloud' ? (
            <>
              <Cloud size={14} className="text-emerald-400" />
              <span className="text-emerald-400">Generated by Qwen Cloud</span>
            </>
          ) : (
            <>
              <Cpu size={14} className="text-amber-400" />
              <span className="text-amber-400">Generated by local fallback</span>
            </>
          )}
          {fallbackReason && (
            <span className="truncate text-slate-600" title={fallbackReason}>
              — {fallbackReason}
            </span>
          )}
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {audioUrl && (
        <div className="mt-4 bg-slate-800 p-2 rounded-lg">
          <audio controls src={audioUrl} className="w-full" autoPlay />
        </div>
      )}
    </main>
  );
};
