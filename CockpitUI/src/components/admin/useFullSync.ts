'use client';

import { useEffect, useRef, useState } from 'react';
import type { PipelineState, StepStatus } from './adminTypes';
import { PIPELINE_STEPS } from './adminConstants';
import { readSSE } from './sseUtils';

const EMPTY_STEP = { status: 'idle' as StepStatus, message: null, startedAt: null, elapsedMs: null };

/** Manages full pipeline execution state and the runPipeline action. */
export function useFullSync() {
  const [states, setStates] = useState<PipelineState>(() =>
    Object.fromEntries(PIPELINE_STEPS.map(s => [s.key, { ...EMPTY_STEP }]))
  );
  const [tick, setTick] = useState(0);
  const running = useRef(false);

  const anyRunning = Object.values(states).some(s => s.status === 'running');
  const allDone    = Object.values(states).every(s => s.status !== 'idle' && s.status !== 'running');
  const anyError   = Object.values(states).some(s => s.status === 'error');

  // Drive a 1 s tick while the pipeline is active — forces elapsed time to re-render
  useEffect(() => {
    if (!anyRunning) return;
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, [anyRunning]);

  function setStep(key: string, status: StepStatus, message: string | null = null, startedAt: number | null = null, elapsedMs: number | null = null) {
    setStates(prev => ({ ...prev, [key]: { status, message, startedAt, elapsedMs } }));
  }

  async function runPipeline() {
    if (running.current) return;
    running.current = true;
    setTick(0);
    setStates(Object.fromEntries(PIPELINE_STEPS.map(s => [s.key, { ...EMPTY_STEP }])));

    const zerodha = PIPELINE_STEPS.find(s => s.key === 'zerodha')!;
    const zerodhaStart = Date.now();
    setStep('zerodha', 'running', null, zerodhaStart);
    try {
      const msg = await readSSE(zerodha.endpoint, zerodha.method, m => setStep('zerodha', 'running', m, zerodhaStart));
      setStep('zerodha', 'ok', msg, zerodhaStart, Date.now() - zerodhaStart);
    } catch (err) {
      setStep('zerodha', 'error', err instanceof Error ? err.message : 'failed', zerodhaStart, Date.now() - zerodhaStart);
      running.current = false;
      return;
    }

    // sync-daily + sync-1min run in parallel (independent data sources)
    const syncDaily = PIPELINE_STEPS.find(s => s.key === 'sync-daily')!;
    const sync1min  = PIPELINE_STEPS.find(s => s.key === 'sync-1min')!;
    const syncStart = Date.now();
    setStep('sync-daily', 'running', null, syncStart);
    setStep('sync-1min',  'running', null, syncStart);

    const [dailyResult, minResult] = await Promise.allSettled([
      readSSE(syncDaily.endpoint, syncDaily.method, msg => setStep('sync-daily', 'running', msg, syncStart)),
      readSSE(sync1min.endpoint,  sync1min.method,  msg => setStep('sync-1min',  'running', msg, syncStart)),
    ]);

    const syncElapsed = Date.now() - syncStart;
    setStep('sync-daily', dailyResult.status === 'fulfilled' ? 'ok' : 'error',
      dailyResult.status === 'fulfilled' ? dailyResult.value : (dailyResult.reason?.message ?? 'failed'),
      syncStart, syncElapsed);
    setStep('sync-1min', minResult.status === 'fulfilled' ? 'ok' : 'error',
      minResult.status === 'fulfilled' ? minResult.value : (minResult.reason?.message ?? 'failed'),
      syncStart, syncElapsed);

    if (dailyResult.status === 'rejected' || minResult.status === 'rejected') {
      running.current = false;
      return;
    }

    // indicators -> setup behavior -> scores run sequentially via SSE
    for (const step of PIPELINE_STEPS.filter(s => s.key === 'indicators' || s.key === 'behavior' || s.key === 'scores')) {
      const startedAt = Date.now();
      setStep(step.key, 'running', null, startedAt);
      try {
        const msg = await readSSE(step.endpoint, step.method, m => setStep(step.key, 'running', m, startedAt));
        setStep(step.key, 'ok', msg, startedAt, Date.now() - startedAt);
      } catch (err) {
        setStep(step.key, 'error', err instanceof Error ? err.message : 'failed', startedAt, Date.now() - startedAt);
        running.current = false;
        return;
      }
    }

    running.current = false;
  }

  return { states, tick, anyRunning, allDone, anyError, runPipeline };
}
