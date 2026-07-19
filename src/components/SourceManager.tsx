import { useState } from 'react';
import { Link, LoaderCircle } from 'lucide-react';
import { importYouTubeSource } from '../api';

export const SourceManager = () => {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('Ready for source audio');
  const [loading, setLoading] = useState(false);

  const handleImport = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setStatus('Downloading and queueing transcription…');
    try {
      const result = await importYouTubeSource(url.trim());
      setStatus(`Source #${result.source_id}: ${result.status}`);
      setUrl('');
    } catch (error) {
      console.error(error);
      setStatus('Import failed. Check backend logs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <label className="block text-xs uppercase tracking-wider text-slate-500 mb-2">
          YouTube source
        </label>
        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://youtube.com/watch?v=…"
          className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-amber-500"
        />
      </div>
      <button
        onClick={handleImport}
        disabled={loading || !url.trim()}
        className="w-full flex items-center justify-center gap-2 rounded-md bg-slate-800 px-3 py-2 text-sm font-semibold hover:bg-slate-700 disabled:opacity-40"
      >
        {loading ? <LoaderCircle size={16} className="animate-spin" /> : <Link size={16} />}
        Import source
      </button>
      <p className="text-xs leading-5 text-slate-500">{status}</p>
    </div>
  );
};
