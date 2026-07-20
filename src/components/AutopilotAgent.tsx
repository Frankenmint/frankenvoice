import { useEffect, useMemo, useState } from 'react';
import { Bot, CheckCircle2, LoaderCircle, ShieldCheck } from 'lucide-react';
import {
  approveAutopilotRun,
  autopilotAudioUrl,
  createAutopilotPlan,
  getAutopilotRun,
  type AutopilotRun,
} from '../api';

export const AutopilotAgent = () => {
  const [goal, setGoal] = useState(
    'Prepare a robotic pirate transmission from the shared corpus. Check vocabulary coverage, use Qwen only to fill missing words, require approval for cloud actions, and keep the final audio word-by-word composite.',
  );
  const [targetText, setTargetText] = useState(
    'Ahoy matey, FrankenVoice is broadcasting from Alibaba Cloud, assembled one fragment at a time.',
  );
  const [sources, setSources] = useState('');
  const [run, setRun] = useState<AutopilotRun | null>(null);
  const [allowSourceImports, setAllowSourceImports] = useState(false);
  const [allowCloudEnrichment, setAllowCloudEnrichment] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourceUrls = useMemo(
    () => sources.split(/\n+/).map((value) => value.trim()).filter(Boolean),
    [sources],
  );

  useEffect(() => {
    if (!run || !['approved', 'executing'].includes(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const updated = await getAutopilotRun(run.id);
        setRun(updated);
        if (['complete', 'failed'].includes(updated.status)) window.clearInterval(timer);
      } catch (pollError) {
        console.error(pollError);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [run?.id, run?.status]);

  const handlePlan = async () => {
    setBusy(true);
    setError(null);
    try {
      setRun(await createAutopilotPlan(goal, targetText, sourceUrls, 3));
    } catch (planError) {
      console.error(planError);
      setError('Qwen could not create the workflow plan. Confirm the API key and agent model.');
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async () => {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      setRun(await approveAutopilotRun(run.id, allowSourceImports, allowCloudEnrichment));
    } catch (approvalError) {
      console.error(approvalError);
      setError('Approval could not be applied. Refresh the run and try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex-1 overflow-y-auto bg-slate-900 p-6">
      <div className="mx-auto max-w-5xl space-y-5">
        <header className="rounded-xl border border-violet-500/30 bg-slate-950 p-5">
          <div className="flex items-center gap-3">
            <Bot className="text-violet-400" />
            <div>
              <h1 className="text-xl font-bold">QWEN AUTOPILOT AGENT</h1>
              <p className="text-sm text-slate-400">
                Qwen plans and enriches the corpus. FrankenVoice assembles final audio from independent fragments.
              </p>
            </div>
          </div>
        </header>

        <section className="grid gap-4 rounded-xl border border-slate-800 bg-slate-950 p-5">
          <label className="text-sm text-slate-300">
            Creative direction / agent objective
            <textarea
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              className="mt-2 h-28 w-full resize-none rounded border border-slate-700 bg-slate-900 p-3"
            />
          </label>
          <label className="text-sm text-slate-300">
            Final line to render
            <textarea
              value={targetText}
              onChange={(event) => setTargetText(event.target.value)}
              className="mt-2 h-28 w-full resize-none rounded border border-slate-700 bg-slate-900 p-3"
            />
          </label>
          <label className="text-sm text-slate-300">
            New source videos — optional, one per line
            <textarea
              value={sources}
              onChange={(event) => setSources(event.target.value)}
              placeholder="Leave blank to use the existing shared corpus"
              className="mt-2 h-20 w-full resize-none rounded border border-slate-700 bg-slate-900 p-3"
            />
            <span className="mt-2 block text-xs text-slate-500">
              Source downloads and paid Qwen enrichment remain blocked until the human checkpoint.
            </span>
          </label>
          <button
            onClick={handlePlan}
            disabled={busy || !goal.trim() || !targetText.trim()}
            className="flex items-center justify-center gap-2 rounded bg-violet-600 px-4 py-3 font-bold hover:bg-violet-500 disabled:opacity-50"
          >
            {busy ? <LoaderCircle className="animate-spin" /> : <Bot />}
            ASK QWEN TO BUILD PLAN
          </button>
        </section>

        {run && (
          <section className="space-y-4 rounded-xl border border-slate-700 bg-slate-950 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest text-violet-400">Qwen plan</p>
                <h2 className="mt-1 text-lg font-semibold">{run.plan.summary}</h2>
              </div>
              <span className="rounded-full border border-slate-700 px-3 py-1 text-xs font-mono uppercase">
                {run.status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-sm text-slate-400">{run.plan.rationale}</p>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded border border-slate-800 bg-slate-900 p-4">
                <p className="mb-2 text-xs uppercase text-slate-500">Planned tools</p>
                <ol className="space-y-2 text-sm">
                  {run.plan.steps.map((step, index) => (
                    <li key={step}>{index + 1}. {step.replace(/_/g, ' ')}</li>
                  ))}
                </ol>
              </div>
              <div className="rounded border border-slate-800 bg-slate-900 p-4">
                <p className="mb-2 text-xs uppercase text-slate-500">Corpus preflight</p>
                <p className="text-sm">External actions: {run.plan.estimated_external_actions}</p>
                <p className="text-sm">Vocabulary entries checked: {run.coverage_before.words.length}</p>
                <p className="text-sm">
                  Missing variants: {run.coverage_before.words.reduce((sum, word) => sum + word.needed, 0)}
                </p>
              </div>
            </div>

            {run.status === 'awaiting_approval' && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                <div className="mb-3 flex items-center gap-2 text-amber-300">
                  <ShieldCheck size={18} /> HUMAN CHECKPOINT
                </div>
                <label className="mb-2 flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={allowSourceImports}
                    onChange={(event) => setAllowSourceImports(event.target.checked)}
                  />
                  Approve downloading and processing supplied source URLs
                </label>
                <label className="mb-4 flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={allowCloudEnrichment}
                    onChange={(event) => setAllowCloudEnrichment(event.target.checked)}
                  />
                  Approve Qwen Cloud requests to fill vocabulary gaps
                </label>
                <button
                  onClick={handleApprove}
                  disabled={busy}
                  className="flex items-center gap-2 rounded bg-amber-500 px-4 py-2 font-bold text-slate-950 disabled:opacity-50"
                >
                  <CheckCircle2 size={18} /> APPROVE AND EXECUTE
                </button>
              </div>
            )}

            <div className="rounded border border-slate-800 bg-slate-900 p-4">
              <p className="mb-3 text-xs uppercase text-slate-500">Agent event log</p>
              <div className="space-y-2 font-mono text-xs text-slate-300">
                {run.events.map((event, index) => (
                  <p key={`${event.type}-${index}`}>[{event.type}] {event.message}</p>
                ))}
              </div>
            </div>

            {run.status === 'complete' && run.result && (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
                <p className="mb-3 text-sm text-emerald-300">{run.result.report}</p>
                <audio controls src={autopilotAudioUrl(run.id)} className="w-full" />
              </div>
            )}

            {run.status === 'failed' && <p className="text-sm text-red-400">{run.error}</p>}
          </section>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    </main>
  );
};
