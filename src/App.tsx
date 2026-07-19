import { useState } from 'react';
import { Composer } from './components/Composer';
import { ConversationReader } from './components/ConversationReader';
import { SourceManager } from './components/SourceManager';
import { VoiceControls } from './components/VoiceControls';

function App() {
  const [mode, setMode] = useState<'composer' | 'reader'>('composer');

  return (
    <div className="flex min-h-screen w-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      <aside className="w-80 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 font-bold tracking-widest text-amber-500">
          FRANKENVOICE
        </div>
        <div className="grid grid-cols-2 gap-2 border-b border-slate-800 p-3">
          <button
            onClick={() => setMode('composer')}
            className={`rounded px-3 py-2 text-xs font-semibold ${mode === 'composer' ? 'bg-violet-600' : 'bg-slate-900 text-slate-400'}`}
          >
            COMPOSER
          </button>
          <button
            onClick={() => setMode('reader')}
            className={`rounded px-3 py-2 text-xs font-semibold ${mode === 'reader' ? 'bg-violet-600' : 'bg-slate-900 text-slate-400'}`}
          >
            READER
          </button>
        </div>
        <SourceManager />
      </aside>

      {mode === 'composer' ? <Composer /> : <ConversationReader />}

      <aside className="w-80 border-l border-slate-800 bg-slate-900 p-6">
        <VoiceControls />
      </aside>
    </div>
  );
}

export default App;
