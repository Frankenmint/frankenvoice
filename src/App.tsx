import { Composer } from './components/Composer';
import { SourceManager } from './components/SourceManager';
import { VoiceControls } from './components/VoiceControls';

function App() {
  return (
    <div className="flex min-h-screen w-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      <aside className="w-80 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 font-bold tracking-widest text-amber-500">
          FRANKENVOICE
        </div>
        <SourceManager />
      </aside>

      <Composer />

      <aside className="w-80 border-l border-slate-800 bg-slate-900 p-6">
        <VoiceControls />
      </aside>
    </div>
  );
}

export default App;
