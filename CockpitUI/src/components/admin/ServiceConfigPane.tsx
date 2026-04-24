'use client';

import { useCallback, useEffect, useState } from 'react';
import type { AdminSection, FieldDef, StepStatus } from './adminTypes';
import { cn } from '@/lib/cn';
import { SERVICE_CONFIGS } from './adminConstants';
import { ConfigField } from './ConfigField';

interface ServiceConfigPaneProps {
  sectionKey: AdminSection;
  /** Server-pre-fetched config to skip the initial load round-trip. */
  initialConfig?: Record<string, unknown> | null;
}

/** Renders a grouped list of config fields for a microservice, with save/reset. */
export function ServiceConfigPane({ sectionKey, initialConfig }: ServiceConfigPaneProps) {
  const def = SERVICE_CONFIGS[sectionKey];
  const [loadStatus, setLoadStatus] = useState<StepStatus>(initialConfig ? 'ok' : 'idle');
  const [saveStatus, setSaveStatus] = useState<StepStatus>('idle');
  const [saveMsg,    setSaveMsg]    = useState<string | null>(null);
  const [config,     setConfig]     = useState<Record<string, unknown> | null>(initialConfig ?? null);

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

  // Skip auto-load when the server already provided initialConfig
  useEffect(() => { if (!initialConfig) load(); }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(key: string, val: unknown) {
    setConfig(prev => prev ? { ...prev, [key]: val } : prev);
  }

  async function save() {
    if (!config || saveStatus === 'running') return;
    setSaveStatus('running'); setSaveMsg(null);
    try {
      const res  = await fetch(def.endpoint, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
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
        <button type="button" onClick={load} className="rounded-lg border border-border px-3 py-1.5 text-[11px] text-ghost hover:border-accent/40 hover:text-fg transition-colors">
          {loadStatus === 'running' ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {loadStatus === 'error' && (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-bear/30 bg-bear/5 px-4 py-3">
          <span className="text-[11px] text-bear">Failed to load config.</span>
          <button type="button" onClick={load} className="text-[11px] text-accent underline">Retry</button>
        </div>
      )}
      {!config && loadStatus !== 'error' && <p className="text-[11px] text-ghost">Loading…</p>}

      {config && (
        <>
          {Object.entries(grouped).map(([groupName, fields]) => (
            <div key={groupName} className="mb-6">
              {groupName && <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-ghost/60">{groupName}</p>}
              <div className="grid grid-cols-2 gap-3">
                {fields.map(f => config[f.key] !== undefined && (
                  <ConfigField key={f.key} def={f} value={config[f.key]} onChange={handleChange} />
                ))}
              </div>
            </div>
          ))}
          <div className="flex items-center gap-4 border-t border-border pt-5">
            <button type="button" onClick={save} disabled={saveStatus === 'running'}
              className={`rounded-lg border px-5 py-2 text-[12px] font-black transition-colors ${saveStatus === 'running' ? 'cursor-not-allowed border-border text-ghost' : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'}`}>
              {saveStatus === 'running' ? 'Saving…' : 'Save & Apply'}
            </button>
            <button type="button" onClick={load} className="text-[11px] text-ghost underline">Reset</button>
            {saveStatus !== 'idle' && saveStatus !== 'running' && saveMsg && (
              <span className={cn('text-[11px] font-black', saveStatus === 'ok' ? 'text-bull' : 'text-bear')}>{saveMsg}</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
