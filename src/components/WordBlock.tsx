import React, { useState } from 'react';
import { RefreshCw, Lock, Unlock, Play } from 'lucide-react';

interface WordBlockProps {
  word: string;
  index: number;
  onReroll: (index: number) => void;
  onPlay: (word: string) => void;
  isLocked: boolean;
  onToggleLock: (index: number) => void;
}

export const WordBlock: React.FC<WordBlockProps> = ({ word, index, onReroll, onPlay, isLocked, onToggleLock }) => {
  return (
    <div className="relative group flex flex-col items-center mx-1">
      <button 
        onClick={() => onPlay(word)}
        className="bg-slate-800 border border-slate-600 hover:border-amber-500 text-slate-200 px-3 py-2 rounded-md font-mono text-lg transition-all shadow-lg active:scale-95 flex items-center gap-2"
      >
        <span className="opacity-50 text-xs">{index + 1}</span>
        {word}
      </button>
      
      {/* Controls Overlay */}
      <div className="absolute -top-3 right-0 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => onToggleLock(index)} className="p-1 bg-slate-700 rounded-full hover:text-amber-400">
          {isLocked ? <Lock size={12} /> : <Unlock size={12} />}
        </button>
        <button onClick={() => onReroll(index)} className="p-1 bg-slate-700 rounded-full hover:text-amber-400">
          <RefreshCw size={12} />
        </button>
      </div>
    </div>
  );
};
