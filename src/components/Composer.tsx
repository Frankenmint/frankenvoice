import { useEffect, useState } from 'react';
import { Download, Play, RefreshCw } from 'lucide-react';
import { generateSpeech } from '../api';
import { WordBlock } from './WordBlock';

export const Composer = () => {
  const [text, setText] = useState(
    'Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo.',
  );
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lockedWords, setLockedWords] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const tokens = text.trim() ? text.trim().split(/\s+/) : [];

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
    try {
      const url = await generateSpeech(text, Math.floor(Math.random() * 1000));
      setAudioUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
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

  return (
    <main className="flex-1 flex flex-col p-6 bg-slate-900 border-r border-slate-800">
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="w-full h-32 bg-slate-800 text-slate-200 p-4 rounded-lg font-mono text-lg mb-6 focus:ring-2 ring-amber-500 outline-none resize-none"
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
            className="flex items-center gap-2 bg-amber-600 hover:bg-amber-500 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-amber-900/20 transition-all disabled:opacity-50"
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

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {audioUrl && (
        <div className="mt-4 bg-slate-800 p-2 rounded-lg">
          <audio controls src={audioUrl} className="w-full" autoPlay />
        </div>
      )}
    </main>
  );
};
