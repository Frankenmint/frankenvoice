import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, CloudCog, Link, LoaderCircle, Sparkles } from 'lucide-react';
import {
  enrichDataset,
  getSourceProgress,
  importYouTubeSource,
  transcribeSourceWithQwen,
  type SourceProgress,
} from '../api';

export const SourceManager = () => {
  const [url, setUrl] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [words, setWords] = useState('');
  const [status, setStatus] = useState('Ready for source audio');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<SourceProgress | null>(null);

  const numericSourceId = Number(sourceId);

  useEffect(() => {
    if (!numericSourceId || !progress || !['pending', 'processing'].includes(progress.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getSourceProgress(numericSourceId);
        setProgress(next);
        setStatus(
          next.status === 'complete'
            ? `Source #${next.id} complete: ${next.clip_count} clips created.`
            : next.status === 'failed'
              ? `Source #${next.id} failed during processing.`
              : `Source #${next.id} processing: ${next.clip_count} clips created so far…`,
        );
        if (['complete', 'failed'].includes(next.status)) window.clearInterval(timer);
      } catch (error) {
        console.error(error);
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [numericSourceId, progress?.status]);

  const handleImport = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setProgress(null);
    setStatus('Downloading YouTube audio. This may take a minute…');
    try {
      const result = await importYouTubeSource(url.trim());
      setSourceId(String(result.source_id));
      const firstProgress = await getSourceProgress(result.source_id);
      setProgress(firstProgress);
      setStatus(`Source #${result.source_id} accepted. Transcribing and extracting clips…`);
      setUrl('');
    } catch (error) {
      console.error(error);
      setStatus('YouTube import failed. Check the URL and backend logs.');
      setProgress({
        id: 0,
        title: url,
        source_type: 'youtube',
        status: 'failed',
        clip_count: 0,
        created_at: '',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleQwenTranscription = async () => {
    if (!numericSourceId || !audioUrl.trim()) return;
    setLoading(true);
    setStatus('Qwen ASR is timestamping the source…');
    try {
      const result = await transcribeSourceWithQwen(numericSourceId, audioUrl.trim());
      setStatus(`Qwen cut ${result.created.length} original word clips from source #${numericSourceId}.`);
    } catch (error) {
      console.error(error);
      setStatus('Qwen transcription failed. Audio URL must be directly reachable.');
    } finally {
      setLoading(false);
    }
  };

  const handleEnrich = async () => {
    if (!words.trim()) return;
    setLoading(true);
    setStatus('Qwen is expanding the shared FrankenVoice vocabulary…');
    try {
      const result = await enrichDataset(words.trim(), 3);
      setStatus(`Added ${result.created.length} clips to ${result.corpus}; ${result.failures.length} failed.`);
    } catch (error) {
      console.error(error);
      setStatus('Enrichment failed. Confirm the Qwen API key and voice list.');
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-violet-500';

  const statusTone = progress?.status === 'failed'
    ? 'border-red-500/30 bg-red-500/10 text-red-300'
    : progress?.status === 'complete'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : 'border-sky-500/30 bg-sky-500/10 text-sky-300';

  return (
    <div className="p-4 space-y-5 overflow-y-auto">
      <section className="space-y-3">
        <label className="block text-xs uppercase tracking-wider text-slate-500">Add a source recording</label>
        <p className="text-xs leading-5 text-slate-500">
          Import a YouTube recording you have permission to use. FrankenVoice extracts reusable word fragments into the shared corpus.
        </p>
        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://youtube.com/watch?v=…"
          className={inputClass}
        />
        <button
          onClick={handleImport}
          disabled={loading || !url.trim()}
          className="w-full flex items-center justify-center gap-2 rounded-md bg-slate-800 px-3 py-2 text-sm font-semibold hover:bg-slate-700 disabled:opacity-40"
        >
          {loading ? <LoaderCircle size={16} className="animate-spin" /> : <Link size={16} />}
          {loading ? 'IMPORTING…' : 'IMPORT SOURCE'}
        </button>

        <div className={`rounded-md border px-3 py-3 text-xs leading-5 ${statusTone}`}>
          <div className="flex items-start gap-2">
            {progress?.status === 'failed'
              ? <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              : progress?.status === 'complete'
                ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
                : <LoaderCircle size={16} className={loading || progress?.status === 'processing' ? 'mt-0.5 shrink-0 animate-spin' : 'mt-0.5 shrink-0'} />}
            <div>
              <p className="font-semibold">{status}</p>
              {progress && progress.id > 0 && (
                <p className="mt-1 font-mono opacity-80">source #{progress.id} · {progress.clip_count} clips · {progress.status}</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-3 border-t border-slate-800 pt-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-violet-400">
          <Sparkles size={14} /> Qwen vocabulary enrichment
        </div>
        <p className="text-xs leading-5 text-slate-500">
          Qwen fills vocabulary gaps with isolated words. Final sentences are still assembled by FrankenVoice from independent fragments.
        </p>
        <textarea
          value={words}
          onChange={(event) => setWords(event.target.value)}
          placeholder="Paste a target line or missing words"
          className={`${inputClass} h-24 resize-none`}
        />
        <button
          onClick={handleEnrich}
          disabled={loading || !words.trim()}
          className="w-full rounded-md bg-violet-600 px-3 py-2 text-sm font-semibold hover:bg-violet-500 disabled:opacity-40"
        >
          Expand shared vocabulary
        </button>
      </section>

      <details className="border-t border-slate-800 pt-4 text-sm">
        <summary className="cursor-pointer select-none text-xs uppercase tracking-wider text-slate-500 hover:text-sky-400">
          Advanced: Qwen ASR from public audio URL
        </summary>
        <div className="mt-3 space-y-3 rounded-md border border-slate-800 bg-slate-950/60 p-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-sky-400">
            <CloudCog size={14} /> Developer ingestion tool
          </div>
          <input
            value={sourceId}
            onChange={(event) => setSourceId(event.target.value)}
            placeholder="Imported source ID"
            inputMode="numeric"
            className={inputClass}
          />
          <input
            value={audioUrl}
            onChange={(event) => setAudioUrl(event.target.value)}
            placeholder="Directly reachable audio URL"
            className={inputClass}
          />
          <button
            onClick={handleQwenTranscription}
            disabled={loading || !numericSourceId || !audioUrl.trim()}
            className="w-full rounded-md border border-sky-500/30 px-3 py-2 text-sm font-semibold text-sky-300 hover:bg-sky-500/10 disabled:opacity-40"
          >
            Transcribe + cut original words
          </button>
        </div>
      </details>
    </div>
  );
};
