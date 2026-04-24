'use client';

import type { PipelineState, StepStatus } from './adminTypes';

/** Color constants for SVG connectors. */
const CONNECTOR_COLOR = 'rgb(var(--border))';
const DASH_PATTERN    = '4 3';

export function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

/** Animated status dot shown inside each pipeline node. */
export function StepDot({ status }: { status: StepStatus }) {
  const color =
    status === 'running' ? 'rgb(var(--amber))' :
    status === 'ok'      ? 'rgb(var(--bull))' :
    status === 'error'   ? 'rgb(var(--bear))' :
                           'rgb(var(--border))';
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${status === 'running' ? 'animate-blink' : ''}`}
      style={{ backgroundColor: color }}
    />
  );
}

/** Single node in the visual pipeline workflow graph. */
export function WorkflowNode({ label, s, tick, idx }: {
  label: string;
  s: PipelineState[string];
  tick: number;
  idx: number;
}) {
  void tick; // forces re-render for live elapsed time display
  const liveMs = s.status === 'running' && s.startedAt ? Date.now() - s.startedAt : null;
  const ms = liveMs ?? s.elapsedMs;
  const borderCol =
    s.status === 'running' ? 'rgb(var(--amber))' :
    s.status === 'ok'      ? 'rgb(var(--bull))' :
    s.status === 'error'   ? 'rgb(var(--bear))' :
                              'rgb(var(--border))';
  return (
    <div className="flex w-44 flex-col gap-1.5 rounded-xl border-2 bg-card px-3.5 py-3 transition-colors" style={{ borderColor: borderCol }}>
      <div className="flex items-center gap-2">
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-border text-[8px] font-black text-ghost">{idx}</span>
        <StepDot status={s.status} />
        <span className="min-w-0 flex-1 text-[11px] font-black leading-tight text-fg">{label}</span>
      </div>
      {(s.message || ms !== null) && (
        <div className="flex items-center gap-1 pl-6">
          {s.message && <span className="min-w-0 flex-1 truncate text-[9px] text-ghost">{s.message}</span>}
          {ms !== null && <span className="ml-auto shrink-0 text-[9px] text-ghost">{formatElapsed(ms)}</span>}
        </div>
      )}
    </div>
  );
}

/** SVG merge connector: two nodes converge into one (w-44 + gap-8 = 384px row). */
export function MergeConnector() {
  return (
    <svg width="384" height="44" className="block">
      <path d="M 88 0 C 88 22, 192 22, 192 44"  fill="none" stroke={CONNECTOR_COLOR} strokeWidth="1.5" strokeDasharray={DASH_PATTERN} />
      <path d="M 296 0 C 296 22, 192 22, 192 44" fill="none" stroke={CONNECTOR_COLOR} strokeWidth="1.5" strokeDasharray={DASH_PATTERN} />
    </svg>
  );
}

/** SVG vertical connector between sequential nodes. */
export function VLine() {
  return (
    <svg width="2" height="36" className="mx-auto block">
      <line x1="1" y1="0" x2="1" y2="36" stroke={CONNECTOR_COLOR} strokeWidth="1.5" strokeDasharray={DASH_PATTERN} />
    </svg>
  );
}
