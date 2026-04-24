'use client';

import { memo, useEffect, useMemo, useState } from 'react';
import type { ExpiryListResponse, OptionChainResponse } from '@/domain/option_chain';
import { assessChain } from '@/lib/chainAssessment';
import { fmt2 } from '@/lib/fmt';
import { ExpirySelector } from './ExpirySelector';
import { OptionChainBody } from './OptionChainBody';

interface OptionChainPanelProps {
  symbol:    string;
  onClose:   () => void;
  embedded?: boolean;
}

const ATM_COUNT = 5;

export const OptionChainPanel = memo(({ symbol, onClose, embedded = false }: OptionChainPanelProps) => {
  const [expiries,    setExpiries]    = useState<string[]>([]);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);
  const [chain,       setChain]       = useState<OptionChainResponse | null>(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  useEffect(() => {
    setLoading(true); setError(null);
    fetch('/api/v1/optionchain/expiries', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol }) })
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((data: ExpiryListResponse) => { setExpiries(data.expiries); setSelectedExp(data.expiries[0] ?? null); })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (!selectedExp) return;
    setLoading(true); setError(null);
    fetch('/api/v1/optionchain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol, expiry: selectedExp }) })
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((data: OptionChainResponse) => setChain(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol, selectedExp]);

  const atmStrike = useMemo(() => {
    if (!chain?.strikes.length) return null;
    return chain.strikes.reduce((best, s) =>
      Math.abs(s.strike_price - chain.spot_price) < Math.abs(best - chain.spot_price) ? s.strike_price : best,
      chain.strikes[0].strike_price,
    );
  }, [chain]);

  const visibleStrikes = useMemo(() => {
    if (!chain || atmStrike == null) return [];
    const idx = chain.strikes.findIndex(s => s.strike_price === atmStrike);
    return idx === -1 ? chain.strikes : chain.strikes.slice(Math.max(0, idx - ATM_COUNT), Math.min(chain.strikes.length, idx + ATM_COUNT + 1));
  }, [chain, atmStrike]);

  const assessment = useMemo(() => chain ? assessChain(visibleStrikes, chain.spot_price) : null, [chain, visibleStrikes]);

  const body = <OptionChainBody chain={chain} visibleStrikes={visibleStrikes} atmStrike={atmStrike} loading={loading} error={error} assessment={assessment} />;

  if (embedded) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border px-4 py-2">
          {chain && <span className="chip num text-accent">Spot {fmt2(chain.spot_price)}</span>}
          {expiries.length > 0 && <ExpirySelector expiries={expiries} selected={selectedExp} onSelect={setSelectedExp} />}
        </div>
        {body}
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="surface-card flex max-h-[88vh] w-[96vw] max-w-[1160px] flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            <span className="text-[10px] font-black uppercase text-ghost">Option chain</span>
            {chain && <span className="chip num text-accent">Spot {fmt2(chain.spot_price)}</span>}
          </div>
          <div className="flex items-center gap-2">
            {expiries.length > 0 && <ExpirySelector expiries={expiries} selected={selectedExp} onSelect={setSelectedExp} />}
            <button type="button" onClick={onClose} className="icon-btn" title="Close" aria-label="Close">x</button>
          </div>
        </div>
        {body}
      </div>
    </div>
  );
});
OptionChainPanel.displayName = 'OptionChainPanel';
