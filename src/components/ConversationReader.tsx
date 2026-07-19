import { useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw, SkipForward, Square } from 'lucide-react';
import { generateSpeech, prepareConversation } from '../api';

interface QueueItem {
  text: string;
  url?: string;
  status: 'waiting' | 'generating' | 'ready' | 'playing' | 'done' | 'failed';
}

export const ConversationReader = () => {
  const [text, setText] = useState('');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPreparing, setIsPreparing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [skipCode, setSkipCode] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const controllersRef = useRef<AbortController[]>([]);
  const queueRef = useRef<QueueItem[]>([]);

  useEffect(() => {
    queueRef.current = queue;
  }, [queue]);

  useEffect(
    () => () => {
      controllersRef.current.forEach((controller) => controller.abort());
      queueRef.current.forEach((item) => item.url && URL.revokeObjectURL(item.url));
    },
    [],
  );

  const updateItem = (index: number, patch: Partial<QueueItem>) => {
    setQueue((items) => items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
  };

  const generateItem = async (index: number) => {
    const item = queueRef.current[index];
    if (!item || item.url || item.status === 'generating') return;
    const controller = new AbortController();
    controllersRef.current.push(controller);
    updateItem(index, { status: 'generating' });
    try {
      const generated = await generateSpeech(
        item.text,
        Math.floor(Math.random() * 100000),
        'robot_radio',
        1,
        1,
        controller.signal,
      );
      updateItem(index, { url: generated.url, status: 'ready' });
    } catch (generationError) {
      if (!controller.signal.aborted) {
        console.error(generationError);
        updateItem(index, { status: 'failed' });
      }
    }
  };

  const prefetch = (startIndex: number) => {
    void generateItem(startIndex);
    void generateItem(startIndex + 1);
  };

  const playIndex = async (index: number) => {
    const item = queueRef.current[index];
    if (!item) return;
    setCurrentIndex(index);
    if (!item.url) {
      await generateItem(index);
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    audio.src = item.url;
    audio.playbackRate = speed;
    updateItem(index, { status: 'playing' });
    setIsPaused(false);
    await audio.play();
    prefetch(index + 1);
  };

  useEffect(() => {
    const item = queue[currentIndex];
    if (item?.status === 'ready' && !isPaused) void playIndex(currentIndex);
  }, [queue, currentIndex, isPaused]);

  const handlePrepare = async () => {
    if (!text.trim()) return;
    stopReader();
    setIsPreparing(true);
    setError(null);
    try {
      const prepared = await prepareConversation(text, 420, skipCode);
      const items = prepared.chunks.map((chunk) => ({ text: chunk, status: 'waiting' as const }));
      setQueue(items);
      queueRef.current = items;
      setCurrentIndex(0);
      prefetch(0);
    } catch (prepareError) {
      console.error(prepareError);
      setError('Could not prepare the conversation. Confirm the backend is running.');
    } finally {
      setIsPreparing(false);
    }
  };

  const stopReader = () => {
    audioRef.current?.pause();
    controllersRef.current.forEach((controller) => controller.abort());
    controllersRef.current = [];
    queueRef.current.forEach((item) => item.url && URL.revokeObjectURL(item.url));
    setQueue([]);
    queueRef.current = [];
    setCurrentIndex(0);
    setIsPaused(false);
  };

  const togglePause = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.playbackRate = speed;
      void audio.play();
      setIsPaused(false);
    } else {
      audio.pause();
      setIsPaused(true);
    }
  };

  const nextChunk = () => {
    const next = currentIndex + 1;
    if (next >= queueRef.current.length) return;
    audioRef.current?.pause();
    updateItem(currentIndex, { status: 'done' });
    setCurrentIndex(next);
    prefetch(next);
  };

  const replayChunk = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    audio.playbackRate = speed;
    void audio.play();
    setIsPaused(false);
  };

  const handleEnded = () => {
    updateItem(currentIndex, { status: 'done' });
    const next = currentIndex + 1;
    if (next < queueRef.current.length) {
      setCurrentIndex(next);
      prefetch(next);
    }
  };

  return (
    <main className="flex-1 overflow-y-auto bg-slate-900 p-6">
      <div className="mx-auto max-w-4xl space-y-5">
        <div>
          <h1 className="text-xl font-bold text-slate-100">CONVERSATION READER</h1>
          <p className="mt-1 text-sm text-slate-500">
            Cleans Markdown, chunks long answers, and preloads the next composite transmission while the current one plays.
          </p>
        </div>

        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Paste an assistant response or any long-form text…"
          className="h-64 w-full resize-y rounded-lg border border-slate-700 bg-slate-950 p-4 font-mono text-sm outline-none focus:border-violet-500"
        />

        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-800 bg-slate-950 p-4">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input type="checkbox" checked={skipCode} onChange={(event) => setSkipCode(event.target.checked)} />
            Skip code blocks
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            Playback speed
            <select
              value={speed}
              onChange={(event) => {
                const nextSpeed = Number(event.target.value);
                setSpeed(nextSpeed);
                if (audioRef.current) audioRef.current.playbackRate = nextSpeed;
              }}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1"
            >
              {[0.75, 1, 1.25, 1.5, 1.75].map((value) => <option key={value} value={value}>{value}×</option>)}
            </select>
          </label>
          <button
            onClick={handlePrepare}
            disabled={isPreparing || !text.trim()}
            className="ml-auto rounded-md bg-violet-600 px-5 py-2 font-semibold hover:bg-violet-500 disabled:opacity-40"
          >
            {isPreparing ? 'PREPARING…' : 'READ WITH FRANKENVOICE'}
          </button>
        </div>

        {queue.length > 0 && (
          <section className="space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-slate-400">
                Chunk {Math.min(currentIndex + 1, queue.length)} / {queue.length}
              </span>
              <div className="flex gap-2">
                <button onClick={togglePause} className="rounded bg-slate-800 p-2" aria-label="Pause or play">
                  {isPaused ? <Play size={18} /> : <Pause size={18} />}
                </button>
                <button onClick={replayChunk} className="rounded bg-slate-800 p-2" aria-label="Replay chunk"><RotateCcw size={18} /></button>
                <button onClick={nextChunk} className="rounded bg-slate-800 p-2" aria-label="Skip chunk"><SkipForward size={18} /></button>
                <button onClick={stopReader} className="rounded bg-red-500/10 p-2 text-red-400" aria-label="Stop"><Square size={18} /></button>
              </div>
            </div>
            <audio ref={audioRef} onEnded={handleEnded} className="hidden" />
            <div className="max-h-72 space-y-2 overflow-y-auto">
              {queue.map((item, index) => (
                <button
                  key={`${index}-${item.text.slice(0, 20)}`}
                  onClick={() => void playIndex(index)}
                  className={`w-full rounded border p-3 text-left text-sm ${
                    index === currentIndex ? 'border-violet-500 bg-violet-500/5' : 'border-slate-800 bg-slate-900'
                  }`}
                >
                  <span className="mr-3 font-mono text-xs uppercase text-slate-500">{item.status}</span>
                  {item.text}
                </button>
              ))}
            </div>
          </section>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    </main>
  );
};
