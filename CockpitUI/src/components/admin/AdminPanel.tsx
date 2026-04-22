'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { ADMIN_CONFIG } from '@/lib/api-config';

// ── Types ─────────────────────────────────────────────────────────────────────

type StepStatus = 'idle' | 'running' | 'ok' | 'error';

type AdminSection =
  | 'full-sync'
  | 'jobs'
  | 'config-scorer'
  | 'config-datasync'
  | 'config-livefeed'
  | 'config-modeling';

interface NavItem {
  key: AdminSection;
  label: string;
  caption: string;
  group?: string;
}

type FieldType = 'int' | 'float' | 'bool' | 'string';

interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  group?: string;
  min?: number;
  max?: number;
  step?: number;
}

interface ServiceConfigDef {
  id: string;
  name: string;
  endpoint: string;
  fields: FieldDef[];
}

// ── Nav definition ────────────────────────────────────────────────────────────

const NAV: NavItem[] = [
  { key: 'full-sync', label: 'Full Sync',  caption: 'Run full pipeline' },
  { key: 'jobs',      label: 'Jobs',       caption: 'Trigger tasks' },
  { key: 'config-scorer',   label: 'Scorer',   caption: 'Scoring params',   group: 'Config' },
  { key: 'config-datasync', label: 'Data Sync',caption: 'Sync params',      group: 'Config' },
  { key: 'config-livefeed', label: 'Live Feed', caption: 'Signal thresholds',group: 'Config' },
  { key: 'config-modeling', label: 'Modeling',  caption: 'Model params',     group: 'Config' },
];

// ── Pipeline steps ─────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { key: 'sync-daily',  label: 'Sync Daily Data',         endpoint: '/datasync/sync/run-sse',           method: 'POST' },
  { key: 'sync-1min',   label: 'Sync 1-Min Data',          endpoint: '/datasync/sync/run-1min-sse',      method: 'POST' },
  { key: 'metrics',     label: 'Recompute Metrics',        endpoint: '/datasync/metrics/recompute-sse',  method: 'POST' },
  { key: 'scores',      label: 'Compute Momentum Scores',  endpoint: '/scorer/scores/compute-sse',       method: 'POST' },
  { key: 'models',      label: 'Run Models',               endpoint: '/modeling/models',                  method: 'GET'  },
] as const;

// ── Service config definitions ────────────────────────────────────────────────

const SERVICE_CONFIGS: Record<string, ServiceConfigDef> = {
  'config-scorer': {
    id: 'scorer',
    name: 'Momentum Scorer',
    endpoint: ADMIN_CONFIG.SCORER,
    fields: [
      { key: 'score_lookback_bars',   label: 'History bars loaded',        type: 'int',   min: 50,  max: 500 },
      { key: 'score_min_bars',        label: 'Min bars required',          type: 'int',   min: 10,  max: 100 },
      { key: 'score_concurrency',     label: 'Parallel scoring workers',   type: 'int',   min: 1,   max: 50 },
      { key: 'rsi_period',            label: 'RSI period',                 type: 'int',   min: 2,   max: 50,  group: 'Indicators' },
      { key: 'macd_fast',             label: 'MACD fast EMA',              type: 'int',   min: 2,   max: 50,  group: 'Indicators' },
      { key: 'macd_slow',             label: 'MACD slow EMA',              type: 'int',   min: 5,   max: 200, group: 'Indicators' },
      { key: 'macd_signal',           label: 'MACD signal EMA',            type: 'int',   min: 2,   max: 50,  group: 'Indicators' },
      { key: 'vol_avg_period',        label: 'Volume avg period',          type: 'int',   min: 5,   max: 100, group: 'Indicators' },
      { key: 'nifty500_benchmark',    label: 'Benchmark symbol',           type: 'string',          group: 'Filters' },
      { key: 'min_avg_daily_turnover',label: 'Min avg daily turnover (₹)', type: 'float', min: 0,   group: 'Filters' },
      { key: 'enable_comfort_scoring',label: 'Enable ML comfort scoring',  type: 'bool',            group: 'Filters' },
    ],
  },
  'config-datasync': {
    id: 'datasync',
    name: 'Data Sync',
    endpoint: ADMIN_CONFIG.DATASYNC,
    fields: [
      { key: 'sync_batch_size',       label: 'Symbols per batch',          type: 'int',   min: 1,   max: 500,   group: 'Sync' },
      { key: 'sync_batch_delay_s',    label: 'Batch delay (s)',            type: 'float', min: 0,   max: 30,    group: 'Sync',     step: 0.1 },
      { key: 'sync_1d_history_days',  label: 'Daily history window (days)',type: 'int',   min: 30,  max: 3650,  group: 'Sync' },
      { key: 'dhan_1min_rate_per_sec',label: 'Dhan 1-min req/sec',         type: 'int',   min: 1,   max: 20,    group: 'Dhan API' },
      { key: 'dhan_daily_budget',     label: 'Daily API budget',           type: 'int',   min: 100, max: 50000, group: 'Dhan API' },
      { key: 'dhan_budget_safety',    label: 'Budget safety buffer',       type: 'int',   min: 0,   max: 1000,  group: 'Dhan API' },
      { key: 'dhan_master_timeout_s', label: 'Master CSV timeout (s)',     type: 'float', min: 5,   max: 120,   group: 'Dhan API', step: 1 },
    ],
  },
  'config-livefeed': {
    id: 'livefeed',
    name: 'Live Feed',
    endpoint: ADMIN_CONFIG.LIVEFEED,
    fields: [
      { key: 'drive_candles',              label: 'Drive candles',              type: 'int',   min: 2,  max: 20,    group: 'Open Drive' },
      { key: 'drive_min_body_ratio',       label: 'Min body ratio',             type: 'float', min: 0,  max: 1,     group: 'Open Drive', step: 0.05 },
      { key: 'drive_confirmed_thresh',     label: 'Confirmed threshold',        type: 'float', min: 0,  max: 1,     group: 'Open Drive', step: 0.05 },
      { key: 'drive_weak_thresh',          label: 'Weak threshold',             type: 'float', min: 0,  max: 1,     group: 'Open Drive', step: 0.05 },
      { key: 'spike_window',               label: 'Volume lookback window',     type: 'int',   min: 5,  max: 100,   group: 'Spike' },
      { key: 'spike_vol_ratio',            label: 'Volume multiplier',          type: 'float', min: 1,  max: 20,    group: 'Spike',      step: 0.1 },
      { key: 'spike_price_pct',            label: 'Min price move %',           type: 'float', min: 0,  max: 10,    group: 'Spike',      step: 0.1 },
      { key: 'spike_cooldown',             label: 'Candle cooldown',            type: 'int',   min: 1,  max: 50,    group: 'Spike' },
      { key: 'absorption_cooldown',        label: 'Absorption cooldown',        type: 'int',   min: 1,  max: 50,    group: 'Absorption' },
      { key: 'absorption_near_pct',        label: 'Near level distance',        type: 'float', min: 0,  max: 0.1,   group: 'Absorption', step: 0.001 },
      { key: 'exhaustion_downtrend_candles',label: 'Downtrend candles',         type: 'int',   min: 2,  max: 20,    group: 'Exhaustion' },
      { key: 'exhaustion_vol_ratio_min',   label: 'Climax vol ratio',           type: 'float', min: 1,  max: 30,    group: 'Exhaustion', step: 0.5 },
      { key: 'exhaustion_lower_lows',      label: 'Lower lows needed',          type: 'int',   min: 1,  max: 10,    group: 'Exhaustion' },
      { key: 'orb_vol_ratio',              label: 'ORB vol ratio',              type: 'float', min: 1,  max: 10,    group: 'Level Breakouts', step: 0.1 },
      { key: 'week52_vol_ratio',           label: '52-wk breakout vol ratio',   type: 'float', min: 1,  max: 10,    group: 'Level Breakouts', step: 0.1 },
      { key: 'camarilla_vol_ratio',        label: 'Camarilla vol ratio',        type: 'float', min: 1,  max: 10,    group: 'Level Breakouts', step: 0.1 },
      { key: 'vwap_vol_ratio',             label: 'VWAP vol ratio',             type: 'float', min: 1,  max: 10,    group: 'Level Breakouts', step: 0.1 },
      { key: 'vwap_hysteresis_min',        label: 'VWAP confirm candles',       type: 'int',   min: 1,  max: 20,    group: 'Level Breakouts' },
      { key: 'range_lookback',             label: 'Range lookback bars',        type: 'int',   min: 2,  max: 30,    group: 'Range' },
      { key: 'range_vol_ratio',            label: 'Range vol ratio',            type: 'float', min: 1,  max: 10,    group: 'Range',          step: 0.1 },
      { key: 'range_max_pct',              label: 'Max range width %',          type: 'float', min: 0,  max: 0.1,   group: 'Range',          step: 0.001 },
      { key: 'min_adv_cr',                 label: 'Min ADV (₹Cr)',              type: 'float', min: 0,  max: 100,   group: 'Noise',          step: 0.5 },
      { key: 'cluster_max_per_candle',     label: 'Max signals/candle',         type: 'int',   min: 1,  max: 20,    group: 'Noise' },
      { key: 'confluence_15m_candles',     label: '15m candles',                type: 'int',   min: 1,  max: 20,    group: 'Confluence' },
      { key: 'confluence_1h_candles',      label: '1h candles',                 type: 'int',   min: 1,  max: 50,    group: 'Confluence' },
      { key: 'confluence_min_move_pct',    label: 'Min move %',                 type: 'float', min: 0,  max: 5,     group: 'Confluence',     step: 0.01 },
      { key: 'candle_minutes',             label: 'Candle size (min)',           type: 'int',   min: 1,  max: 60,    group: 'Feed' },
      { key: 'dhan_ws_batch_size',         label: 'WS subscription batch',      type: 'int',   min: 50, max: 1000,  group: 'Feed' },
      { key: 'dhan_reconnect_delay_s',     label: 'WS reconnect delay (s)',     type: 'float', min: 1,  max: 60,    group: 'Feed',           step: 0.5 },
      { key: 'candle_write_batch_size',    label: 'Candle write batch',         type: 'int',   min: 10, max: 1000,  group: 'Feed' },
      { key: 'candle_write_flush_s',       label: 'Candle flush interval (s)',  type: 'float', min: 1,  max: 30,    group: 'Feed',           step: 0.5 },
    ],
  },
  'config-modeling': {
    id: 'modeling',
    name: 'Modeling',
    endpoint: ADMIN_CONFIG.MODELING,
    fields: [
      { key: 'auto_retrain_enabled',                  label: 'Auto-retrain enabled',       type: 'bool' },
      { key: 'max_model_age_days',                    label: 'Max model age (days)',        type: 'int',   min: 1,   max: 365 },
      { key: 'training_concurrency',                  label: 'Training concurrency',       type: 'int',   min: 1,   max: 8 },
      { key: 'score_concurrency',                     label: 'Scoring concurrency',        type: 'int',   min: 1,   max: 100 },
      { key: 'comfort_scorer_retrain_threshold_rmse', label: 'RMSE retrain threshold',     type: 'float', min: 0,   max: 50,     group: 'Comfort Scorer', step: 0.5 },
      { key: 'comfort_scorer_shadow_days',            label: 'Shadow transition days',     type: 'int',   min: 1,   max: 30,     group: 'Comfort Scorer' },
      { key: 'comfort_scorer_min_train_samples',      label: 'Min training samples',       type: 'int',   min: 100, max: 500000, group: 'Comfort Scorer' },
      { key: 'regime_classifier_cache_ttl',           label: 'Regime cache TTL (s)',       type: 'int',   min: 30,  max: 3600,   group: 'Regime Classifier' },
      { key: 'pattern_detector_confidence_threshold', label: 'Pattern confidence',         type: 'float', min: 0,   max: 1,      group: 'Pattern Detector', step: 0.05 },
    ],
  },
};

// ── Shared primitives ─────────────────────────────────────────────────────────

function StepDot({ status }: { status: StepStatus }) {
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

function SectionHeader({ title, caption }: { title: string; caption: string }) {
  return (
    <div className="mb-6">
      <h2 className="text-[15px] font-black text-fg">{title}</h2>
      <p className="mt-1 text-[11px] text-ghost">{caption}</p>
    </div>
  );
}

// ── Full Sync pane ────────────────────────────────────────────────────────────

type PipelineState = Record<string, { status: StepStatus; message: string | null; startedAt: number | null; elapsedMs: number | null }>;

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

// ── Workflow graph primitives ──────────────────────────────────────────────────

const _C = 'rgb(var(--border))'; // connector color
const _D = '4 3';                // dash pattern

function WorkflowNode({ label, s, tick, idx }: {
  label: string;
  s: PipelineState[string];
  tick: number;
  idx: number;
}) {
  void tick; // forces re-render for live elapsed
  const liveMs = s.status === 'running' && s.startedAt ? Date.now() - s.startedAt : null;
  const ms = liveMs ?? s.elapsedMs;
  const borderCol =
    s.status === 'running' ? 'rgb(var(--amber))' :
    s.status === 'ok'      ? 'rgb(var(--bull))' :
    s.status === 'error'   ? 'rgb(var(--bear))' :
                              'rgb(var(--border))';
  return (
    <div
      className="flex w-44 flex-col gap-1.5 rounded-xl border-2 bg-card px-3.5 py-3 transition-colors"
      style={{ borderColor: borderCol }}
    >
      <div className="flex items-center gap-2">
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-border text-[8px] font-black text-ghost">
          {idx}
        </span>
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

// node w-44 = 176px, gap-8 = 32px → row = 384px, each center at 88 and 296, mid at 192
function MergeConnector() {
  return (
    <svg width="384" height="44" className="block">
      <path d="M 88 0 C 88 22, 192 22, 192 44"  fill="none" stroke={_C} strokeWidth="1.5" strokeDasharray={_D} />
      <path d="M 296 0 C 296 22, 192 22, 192 44" fill="none" stroke={_C} strokeWidth="1.5" strokeDasharray={_D} />
    </svg>
  );
}

function VLine() {
  return (
    <svg width="2" height="36" className="mx-auto block">
      <line x1="1" y1="0" x2="1" y2="36" stroke={_C} strokeWidth="1.5" strokeDasharray={_D} />
    </svg>
  );
}

async function readSSE(
  endpoint: string,
  method: string,
  onProgress: (msg: string) => void,
): Promise<string> {
  const res = await fetch(endpoint, { method });
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail ?? data?.message ?? `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) throw new Error('SSE stream closed without completion event');
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let evt: { status: string; message?: string };
      try { evt = JSON.parse(line.slice(6)); } catch { continue; }
      if (evt.status === 'running' && evt.message) onProgress(evt.message);
      else if (evt.status === 'ok') return evt.message ?? 'done';
      else if (evt.status === 'error') throw new Error(evt.message ?? 'failed');
    }
  }
}

function FullSyncPane() {
  const emptyStep = { status: 'idle' as StepStatus, message: null, startedAt: null, elapsedMs: null };
  const [states, setStates] = useState<PipelineState>(() =>
    Object.fromEntries(PIPELINE_STEPS.map(s => [s.key, { ...emptyStep }]))
  );
  const [tick, setTick] = useState(0);
  const running = useRef(false);

  const anyRunning = Object.values(states).some(s => s.status === 'running');
  const allDone = Object.values(states).every(s => s.status !== 'idle' && s.status !== 'running');
  const anyError = Object.values(states).some(s => s.status === 'error');

  useEffect(() => {
    if (!anyRunning) return;
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, [anyRunning]);

  function setStep(
    key: string,
    status: StepStatus,
    message: string | null = null,
    startedAt: number | null = null,
    elapsedMs: number | null = null,
  ) {
    setStates(prev => ({ ...prev, [key]: { status, message, startedAt, elapsedMs } }));
  }

  async function runPipeline() {
    if (running.current) return;
    running.current = true;
    setTick(0);
    setStates(Object.fromEntries(PIPELINE_STEPS.map(s => [s.key, { ...emptyStep }])));

    // sync-daily + sync-1min in parallel (independent data sources)
    const syncDaily = PIPELINE_STEPS.find(s => s.key === 'sync-daily')!;
    const sync1min  = PIPELINE_STEPS.find(s => s.key === 'sync-1min')!;
    const syncStart = Date.now();
    setStep('sync-daily', 'running', null, syncStart);
    setStep('sync-1min',  'running', null, syncStart);

    const [dailyResult, minResult] = await Promise.allSettled([
      readSSE(syncDaily.endpoint, syncDaily.method, msg =>
        setStep('sync-daily', 'running', msg, syncStart)
      ),
      readSSE(sync1min.endpoint, sync1min.method, msg =>
        setStep('sync-1min', 'running', msg, syncStart)
      ),
    ]);

    const syncElapsed = Date.now() - syncStart;
    if (dailyResult.status === 'fulfilled') {
      setStep('sync-daily', 'ok', dailyResult.value, syncStart, syncElapsed);
    } else {
      setStep('sync-daily', 'error', dailyResult.reason?.message ?? 'failed', syncStart, syncElapsed);
    }
    if (minResult.status === 'fulfilled') {
      setStep('sync-1min', 'ok', minResult.value, syncStart, syncElapsed);
    } else {
      setStep('sync-1min', 'error', minResult.reason?.message ?? 'failed', syncStart, syncElapsed);
    }
    if (dailyResult.status === 'rejected' || minResult.status === 'rejected') {
      running.current = false;
      return;
    }

    // metrics → scores: sequential via SSE
    const seqSteps = PIPELINE_STEPS.filter(s => s.key === 'metrics' || s.key === 'scores');
    for (const step of seqSteps) {
      const startedAt = Date.now();
      setStep(step.key, 'running', null, startedAt);
      try {
        const msg = await readSSE(step.endpoint, step.method, m =>
          setStep(step.key, 'running', m, startedAt)
        );
        setStep(step.key, 'ok', msg, startedAt, Date.now() - startedAt);
      } catch (err) {
        setStep(step.key, 'error', err instanceof Error ? err.message : 'failed', startedAt, Date.now() - startedAt);
        running.current = false;
        return;
      }
    }

    const modelsStart = Date.now();
    setStep('models', 'running', null, modelsStart);
    try {
      const res = await fetch('/modeling/models');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : (Array.isArray(data?.models) ? data.models : []);
      const modelNames: string[] = list
        .map((m: { name?: string } | string) => typeof m === 'string' ? m : m.name ?? '')
        .filter(Boolean);

      if (modelNames.length === 0) {
        setStep('models', 'ok', 'no models registered', modelsStart, Date.now() - modelsStart);
      } else {
        await Promise.allSettled(
          modelNames.map(name => fetch(`/modeling/models/${name}/score-all`, { method: 'POST' }))
        );
        setStep('models', 'ok', `${modelNames.length} model(s) scored`, modelsStart, Date.now() - modelsStart);
      }
    } catch (err) {
      setStep('models', 'error', err instanceof Error ? err.message : 'failed', modelsStart, Date.now() - modelsStart);
    }

    running.current = false;
  }

  void tick;

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
        caption="Sync runs in parallel. Scores → metrics → models run sequentially after."
      />

      {/* Run button */}
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
          <span
            className="text-[12px] font-black"
            style={{ color: anyError ? 'rgb(var(--bear))' : 'rgb(var(--bull))' }}
          >
            {anyError ? 'Pipeline failed' : 'Pipeline complete'}
          </span>
        )}
      </div>

      {/* Workflow graph */}
      <div className="flex flex-col items-center">

        {/* Parallel row: sync-daily + sync-1min */}
        <div className="relative flex gap-8">
          <div className="absolute -top-5 left-0 right-0 flex justify-center">
            <span className="rounded-full border border-border bg-card px-2 py-0.5 text-[8px] font-black tracking-widest text-ghost">
              PARALLEL
            </span>
          </div>
          {node('sync-daily', 1)}
          {node('sync-1min',  2)}
        </div>

        {/* Merge → metrics */}
        <MergeConnector />
        {node('metrics', 3)}

        {/* metrics → scores */}
        <VLine />
        {node('scores', 4)}

        {/* scores → models */}
        <VLine />
        {node('models', 5)}

      </div>
    </div>
  );
}

// ── Jobs pane ─────────────────────────────────────────────────────────────────

interface JobAction {
  key: string;
  label: string;
  caption: string;
  endpoint: string;
  method: string;
}

const JOB_ACTIONS: JobAction[] = [
  {
    key: 'sync-daily',
    label: 'Sync Daily Data',
    caption: 'Fetch OHLCV from yfinance for all symbols. Auto-classifies and fills gaps.',
    endpoint: '/datasync/sync/run',
    method: 'POST',
  },
  {
    key: 'sync-1min',
    label: 'Sync 1-Min Data',
    caption: 'Fetch 1-min OHLCV from Dhan for all F&O stocks (last 90 days).',
    endpoint: '/datasync/sync/run-1min',
    method: 'POST',
  },
  {
    key: 'compute-scores',
    label: 'Compute Momentum Scores',
    caption: 'Run unified daily momentum scoring for all symbols.',
    endpoint: '/scorer/scores/compute',
    method: 'POST',
  },
  {
    key: 'recompute-metrics',
    label: 'Recompute Metrics',
    caption: 'Recompute symbol_metrics table from price data.',
    endpoint: '/datasync/metrics/recompute',
    method: 'POST',
  },
];

function JobCard({ action }: { action: JobAction }) {
  const [status, setStatus] = useState<StepStatus>('idle');
  const [msg, setMsg] = useState<string | null>(null);

  async function run() {
    if (status === 'running') return;
    setStatus('running'); setMsg(null);
    try {
      const res = await fetch(action.endpoint, { method: action.method });
      const data = await res.json().catch(() => null);
      if (!res.ok) { setStatus('error'); setMsg(String(data?.detail ?? data?.message ?? `HTTP ${res.status}`)); return; }
      setStatus('ok'); setMsg(String(data?.message ?? data?.status ?? 'started'));
    } catch (err) {
      setStatus('error'); setMsg(err instanceof Error ? err.message : 'Network error');
    }
  }

  const busy = status === 'running';
  const statusColor =
    status === 'running' ? 'rgb(var(--amber))' :
    status === 'ok'      ? 'rgb(var(--bull))' :
    status === 'error'   ? 'rgb(var(--bear))' : '';

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-[13px] font-black text-fg">{action.label}</h3>
          <p className="mt-1 text-[11px] text-ghost leading-relaxed">{action.caption}</p>
          {status !== 'idle' && msg && (
            <p className="mt-2 text-[10px]" style={{ color: statusColor }}>{msg}</p>
          )}
        </div>
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-4 py-1.5 text-[12px] font-black transition-colors ${
            busy
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {busy ? 'Running…' : 'Run'}
        </button>
      </div>
    </div>
  );
}

function TokenCard() {
  const [token, setToken] = useState('');
  const [status, setStatus] = useState<StepStatus>('idle');
  const [msg, setMsg] = useState<string | null>(null);

  async function submit() {
    const value = token.trim();
    if (!value || status === 'running') return;
    setStatus('running'); setMsg(null);
    try {
      const res = await fetch('/api/v1/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: value }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) { setStatus('error'); setMsg(String(data?.detail ?? data?.message ?? `HTTP ${res.status}`)); return; }
      setToken(''); setStatus('ok'); setMsg(data?.message ?? 'Token updated');
    } catch (err) {
      setStatus('error'); setMsg(err instanceof Error ? err.message : 'Network error');
    }
  }

  const busy = status === 'running';
  const statusColor = status === 'ok' ? 'rgb(var(--bull))' : 'rgb(var(--bear))';

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-[13px] font-black text-fg">Update Dhan Token</h3>
      <p className="mt-1 text-[11px] text-ghost leading-relaxed">
        LiveFeed WebSocket feeds reconnect immediately on update.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          type="password"
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="Paste access token…"
          className="field h-8 min-w-0 flex-1 text-[12px]"
          disabled={busy}
          onKeyDown={e => { if (e.key === 'Enter') submit(); }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={busy || !token.trim()}
          className={`shrink-0 rounded-lg border px-4 py-1.5 text-[12px] font-black transition-colors ${
            busy || !token.trim()
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {busy ? 'Updating…' : 'Update'}
        </button>
      </div>
      {status !== 'idle' && msg && (
        <p className="mt-2 text-[10px] font-black" style={{ color: statusColor }}>{msg}</p>
      )}
    </div>
  );
}

function JobsPane() {
  return (
    <div className="max-w-lg">
      <SectionHeader title="Jobs" caption="Trigger background tasks. All run async — check service logs for progress." />
      <div className="flex flex-col gap-3">
        {JOB_ACTIONS.map(a => <JobCard key={a.key} action={a} />)}
        <TokenCard />
      </div>
    </div>
  );
}

// ── Config pane ───────────────────────────────────────────────────────────────

function ConfigField({
  def,
  value,
  onChange,
}: {
  def: FieldDef;
  value: unknown;
  onChange: (key: string, val: unknown) => void;
}) {
  if (def.type === 'bool') {
    return (
      <div className="col-span-2 flex items-center justify-between rounded-lg border border-border bg-base/40 px-3 py-2.5">
        <span className="text-[11px] text-ghost">{def.label}</span>
        <button
          type="button"
          role="switch"
          aria-checked={!!value}
          onClick={() => onChange(def.key, !value)}
          className={`relative h-4 w-7 shrink-0 rounded-full transition-colors ${value ? 'bg-accent' : 'bg-border'}`}
        >
          <span
            className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform ${value ? 'translate-x-3' : 'translate-x-0.5'}`}
          />
        </button>
      </div>
    );
  }

  if (def.type === 'string') {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] text-ghost">{def.label}</span>
        <input
          type="text"
          className="field h-8 w-full text-[12px]"
          value={String(value ?? '')}
          onChange={e => onChange(def.key, e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] text-ghost">{def.label}</span>
      <input
        type="number"
        className="field h-8 w-full num text-[12px]"
        value={value as number}
        min={def.min}
        max={def.max}
        step={def.step ?? (def.type === 'int' ? 1 : 0.01)}
        onChange={e => {
          const raw = def.type === 'int' ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
          onChange(def.key, isNaN(raw) ? value : raw);
        }}
      />
    </div>
  );
}

function ServiceConfigPane({ sectionKey }: { sectionKey: AdminSection }) {
  const def = SERVICE_CONFIGS[sectionKey];
  const [loadStatus, setLoadStatus] = useState<StepStatus>('idle');
  const [saveStatus, setSaveStatus] = useState<StepStatus>('idle');
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async () => {
    setLoadStatus('running');
    try {
      const res = await fetch(def.endpoint);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setConfig(await res.json());
      setLoadStatus('ok');
    } catch {
      setLoadStatus('error');
    }
  }, [def.endpoint]);

  // Auto-load on mount
  useEffect(() => { load(); }, [load]);

  function handleChange(key: string, val: unknown) {
    setConfig(prev => prev ? { ...prev, [key]: val } : prev);
  }

  async function save() {
    if (!config || saveStatus === 'running') return;
    setSaveStatus('running'); setSaveMsg(null);
    try {
      const res = await fetch(def.endpoint, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail ?? data?.message ?? `HTTP ${res.status}`;
        setSaveStatus('error');
        setSaveMsg(typeof detail === 'object' ? JSON.stringify(detail) : String(detail));
        return;
      }
      setConfig(data);
      setSaveStatus('ok'); setSaveMsg('Saved and applied');
    } catch (err) {
      setSaveStatus('error'); setSaveMsg(err instanceof Error ? err.message : 'Network error');
    }
  }

  // Group fields
  const grouped = def.fields.reduce<Record<string, FieldDef[]>>((acc, f) => {
    const g = f.group ?? '';
    (acc[g] ??= []).push(f);
    return acc;
  }, {});

  return (
    <div className="max-w-xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-[15px] font-black text-fg">{def.name} Config</h2>
          <p className="mt-1 text-[11px] text-ghost">{def.fields.length} parameters — persisted to DB, applied immediately</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-border px-3 py-1.5 text-[11px] text-ghost hover:border-accent/40 hover:text-fg transition-colors"
        >
          {loadStatus === 'running' ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {loadStatus === 'error' && (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-bear/30 bg-bear/5 px-4 py-3">
          <span className="text-[11px] text-bear">Failed to load config.</span>
          <button type="button" onClick={load} className="text-[11px] text-accent underline">Retry</button>
        </div>
      )}

      {!config && loadStatus !== 'error' && (
        <p className="text-[11px] text-ghost">Loading…</p>
      )}

      {config && (
        <>
          {Object.entries(grouped).map(([groupName, fields]) => (
            <div key={groupName} className={groupName ? 'mb-6' : 'mb-6'}>
              {groupName && (
                <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-ghost/60">
                  {groupName}
                </p>
              )}
              <div className="grid grid-cols-2 gap-3">
                {fields.map(f => {
                  const val = config[f.key];
                  if (val === undefined) return null;
                  return (
                    <ConfigField key={f.key} def={f} value={val} onChange={handleChange} />
                  );
                })}
              </div>
            </div>
          ))}

          <div className="flex items-center gap-4 border-t border-border pt-5">
            <button
              type="button"
              onClick={save}
              disabled={saveStatus === 'running'}
              className={`rounded-lg border px-5 py-2 text-[12px] font-black transition-colors ${
                saveStatus === 'running'
                  ? 'cursor-not-allowed border-border text-ghost'
                  : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
              }`}
            >
              {saveStatus === 'running' ? 'Saving…' : 'Save & Apply'}
            </button>
            <button type="button" onClick={load} className="text-[11px] text-ghost underline">
              Reset
            </button>
            {saveStatus !== 'idle' && saveStatus !== 'running' && saveMsg && (
              <span
                className="text-[11px] font-black"
                style={{ color: saveStatus === 'ok' ? 'rgb(var(--bull))' : 'rgb(var(--bear))' }}
              >
                {saveMsg}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Root panel ────────────────────────────────────────────────────────────────

export function AdminPanel() {
  const [section, setSection] = useState<AdminSection>('full-sync');

  const groupedNav = NAV.reduce<{ ungrouped: NavItem[]; grouped: Record<string, NavItem[]> }>(
    (acc, item) => {
      if (!item.group) acc.ungrouped.push(item);
      else (acc.grouped[item.group] ??= []).push(item);
      return acc;
    },
    { ungrouped: [], grouped: {} }
  );

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">

      {/* Left nav */}
      <aside className="w-44 shrink-0 border-r border-border bg-panel/60 p-2 overflow-y-auto">
        <nav className="flex flex-col gap-0.5">
          {groupedNav.ungrouped.map(item => (
            <NavButton key={item.key} item={item} active={section === item.key} onClick={() => setSection(item.key)} />
          ))}

          {Object.entries(groupedNav.grouped).map(([groupName, items]) => (
            <div key={groupName} className="mt-3">
              <p className="mb-1 px-2 text-[9px] font-black uppercase tracking-widest text-ghost/50">
                {groupName}
              </p>
              {items.map(item => (
                <NavButton key={item.key} item={item} active={section === item.key} onClick={() => setSection(item.key)} />
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* Content pane */}
      <div className="min-w-0 flex-1 overflow-y-auto p-6">
        {section === 'full-sync' && <FullSyncPane />}
        {section === 'jobs'      && <JobsPane />}
        {(section === 'config-scorer' || section === 'config-datasync' || section === 'config-livefeed' || section === 'config-modeling') && (
          <ServiceConfigPane key={section} sectionKey={section} />
        )}
      </div>

    </div>
  );
}

function NavButton({ item, active, onClick }: { item: NavItem; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${
        active
          ? 'border-accent/40 bg-accent/10 text-fg'
          : 'border-transparent text-dim hover:border-border hover:bg-lift/60 hover:text-fg'
      }`}
    >
      <span className="block text-[12px] font-black leading-tight">{item.label}</span>
      <span className="mt-0.5 block text-[10px] text-ghost">{item.caption}</span>
    </button>
  );
}
