import React, { useState } from 'react';
import { WordBlock } from './WordBlock';
import { generateSpeech } from '../api';
import { Play, Download, RefreshCw } from 'lucide-react';

export const Composer = () => {
  const [text, setText] = useState("Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo.");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lockedWords, setLockedWords] = useState<number[]>([]);
  
  // Parse text into tokens for display
  const tokens = text.split(/\s+/);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      // In a real app, we'd send locked word IDs to backend to preserve them
      // For MVP, we just regenerate the whole string
      const url = await generateSpeech(text, Math.floor(Math.random() * 1000));
      setAudioUrl(url);
    } catch (e) {
      console.error(e);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!audioUrl) return;
    const a = document.createElement('a');
    a.href = audioUrl;
    a.download = 'frankenvoice_export.wav';
    a.click();
  };

  return (
    <div className="flex-1 flex flex-col p-6 bg-slate-900 border-r border-slate-800">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full h-32 bg-slate-800 text-slate-200 p-4 rounded-lg font-mono text-lg mb-6 focus:ring-2 ring-amber-500 outline-none resize-none"
        placeholder="Enter text to fragment..."
      />

      {/* Visual Word Blocks */}
      <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-6 overflow-y-auto flex flex-wrap content-start gap-y-4">
        {tokens.map((token, i) => (
          <WordBlock 
            key={i} 
            word={token} 
            index={i} 
            onReroll={(idx) => console.log("Reroll", idx)} 
            onPlay={(w) => console.log("Preview", w)}
            isLocked={lockedWords.includes(i)}
            onToggleLock={(idx) => {
                if(lockedWords.includes(idx)) setLockedWords(lockedWords.filter(x => x !== idx))
                else setLockedWords([...lockedWords, idx])
            }}
          />
        ))}
      </div>

      {/* Action Bar */}
      <div className="mt-6 flex justify-between items-center">
        <div className="text-slate-500 text-sm font-mono">
          {tokens.length} fragments ready
        </div>
        <div className="flex gap-3">
           <button 
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 bg-amber-600 hover:bg-amber-500 text-white px-6 py-3 rounded-lg font-bold shadow-lg shadow-amber-900/20 transition-all disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />}
            GENERATE TRANSMISSION
          </button>
          
          {audioUrl && (
             <button onClick={handleDownload} className="p-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300">
                <Download />
             </button>
          )}
        </div>
      </div>
      
      {/* Audio Player */}
      {audioUrl && (
        <div className="mt-4 bg-slate-800 p-2 rounded-lg">
            <audio controls src={audioUrl} className="w-full" autoPlay />
        </div>
      )}
    </div>
  );
};
