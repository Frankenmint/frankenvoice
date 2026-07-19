import { useState } from 'react';
import { CloudCog, Link, LoaderCircle, Sparkles } from 'lucide-react';
import {
  enrichDataset,
  importYouTubeSource,
  transcribeSourceWithQwen,
} from '../api';

export const SourceManager = () => {
  const [url, setUrl] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [words, setWords] = useState('');
  const [status, setStatus] = useState('Ready for source audio');
  const [loading, setLoading] = useState(false);

  const numericSourceId = Number(sourceId);

  const handleImport = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setStatus('Downloading and queueing local transcription…');
    try {
      const result = await importYouTubeSource(url.trim());
      setSourceId(String(result.source_id));
      setStatus(`Source #${result.source_id}: ${result.status}`);
      setUrl('');
    } catch (error) {
      console.error(error);
      setStatus('Import failed. Check backend logs.');
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

  return (
    <div className="p-4 space-y-5 overflow-y-auto">
      <section className="space-y-3">
        <label className="block text-xs uppercase tracking-wider text-slate-500">YouTube source</label>
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
          Import source
        </button>
      </section>

      <section className="space-y-3 border-t border-slate-800 pt-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-sky-400">
          <CloudCog size={14} /> Qwen ASR
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
      </section>

      <section className="space-y-3 border-t border-slate-800 pt-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-violet-400">
          <Sparkles size={14} /> Global vocabulary enrichment
        </div>
        <p className="text-xs leading-5 text-slate-500">
          No speaker profile. Every generated word joins the same changing FrankenVoice corpus.
        </p>
        <textarea
          value={words}
          onChange={(event) => setWords(event.target.value)}
          placeholder="Paste target text or missing words"
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

      <p className="text-xs leading-5 text-slate-500">{status}</p>
    </div>
  );
};
