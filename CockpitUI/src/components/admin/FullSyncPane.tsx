'use client';

import { cn } from '@/lib/cn';
import { PIPELINE_STEPS } from './adminConstants';
import { WorkflowNode, MergeConnector, VLine } from './WorkflowGraph';
import { useFullSync } from './useFullSync';

/** Section header shared between admin panes. */
export function SectionHeader({ title, caption }: { title: string; caption: string }) {
  return (
    <div className="mb-6">
      <h2 className="text-[15px] font-black text-fg">{title}</h2>
      <p className="mt-1 text-[11px] text-ghost">{caption}</p>
    </div>
  );
}

/**
 * Renders the full pipeline runner: parallel sync → sequential
 * indicators/setup behavior/scores, with a live workflow graph.
 */
export function FullSyncPane() {
  const { states, tick, anyRunning, allDone, anyError, runPipeline } = useFullSync();

  const node = (key: string, idx: number) => (
    <WorkflowNode
      label={PIPELINE_STEPS.find(s => s.key === key)!.label}
      s={states[key]}
      tick={tick}
      idx={idx}
    />
  );

  return (
    <div>
      <SectionHeader
        title="Full Pipeline"
        caption="Sync runs in parallel. Indicators, setup behavior, rankings, and models run sequentially after."
      />
      <div className="mb-10 flex items-center gap-4">
        <button
          type="button"
          onClick={runPipeline}
          disabled={anyRunning}
          className={`rounded-lg border px-6 py-2.5 text-[13px] font-black transition-colors ${
            anyRunning
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {anyRunning ? 'Running…' : 'Run Pipeline'}
        </button>
        {allDone && (
          <span className={cn('text-[12px] font-black', anyError ? 'text-bear' : 'text-bull')}>
            {anyError ? 'Pipeline failed' : 'Pipeline complete'}
          </span>
        )}
      </div>

      <div className="flex flex-col items-center">
        {node('zerodha', 0)}
        <VLine />
        <div className="relative flex gap-8">
          <div className="absolute -top-5 left-0 right-0 flex justify-center">
            <span className="rounded-full border border-border bg-card px-2 py-0.5 text-[8px] font-black tracking-widest text-ghost">PARALLEL</span>
          </div>
          {node('sync-daily', 1)}
          {node('sync-1min',  2)}
        </div>
        <MergeConnector />
        {node('indicators', 3)}
        <VLine />
        {node('behavior', 4)}
        <VLine />
        {node('scores', 5)}
      </div>
    </div>
  );
}

