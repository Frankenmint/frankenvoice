import React from 'react';
import { Composer } from './components/Composer';
import { VoiceControls } from './components/VoiceControls'; // Assume implemented similarly to Composer
import { SourceManager } from './components/SourceManager'; // Assume implemented

function App() {
  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* Left Panel: Sources */}
      <div className="w-80 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 font-bold tracking-widest text-amber-500">
          FRANKENVOICE
        </div>
        <SourceManager />
      </div>

      {/* Center Panel: Composer */}
      <Composer />

      {/* Right Panel: Controls */}
      <div className="w-80 border-l border-slate-800 bg-slate-900 p-6">
        <VoiceControls />
      </div>
    </div>
  );
}

export default App;
