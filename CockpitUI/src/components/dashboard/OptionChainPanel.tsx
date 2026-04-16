'use client';

import { memo, useCallback, useEffect, useState } from 'react';
import type { ExpiryListResponse, OptionChainResponse, OptionStrike } from '@/domain/option_chain';
import { fmt2 } from '@/lib/fmt';

interface OptionChainPanelProps {
  symbol: string;
  onClose: () => void;
}

export const OptionChainPanel = memo(({ symbol, onClose }: OptionChainPanelProps) => {
  const [expiries,     setExpiries]     = useState<string[]>([]);
  const [selectedExp,  setSelectedExp]  = useState<string | null>(null);
  const [chain,        setChain]        = useState<OptionChainResponse | null>(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);

  // Load expiries on mount
  useEffect(() => {
    setLoading(true);
    fetch('/api/v1/optionchain/expiries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    })
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((data: ExpiryListResponse) => {
        setExpiries(data.expiries);
        if (data.expiries.length > 0) setSelectedExp(data.expiries[0]);
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [symbol]);

  // Load chain when expiry changes
  useEffect(() => {
    if (!selectedExp) return;
    setLoading(true);
    fetch('/api/v1/optionchain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, expiry: selectedExp }),
    })
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((data: OptionChainResponse) => { setChain(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [symbol, selectedExp]);

  const findATM = useCallback(() => {
    if (!chain) return null;
    let closest = chain.strikes[0];
    for (const s of chain.strikes) {
      if (Math.abs(s.strike_price - chain.spot_price) < Math.abs(closest.strike_price - chain.spot_price)) {
        closest = s;
      }
    }
    return closest?.strike_price ?? null;
  }, [chain]);

  const atmStrike = findATM();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,12,24,0.88)' }} onClick={onClose}>
      <div className="w-[95vw] max-w-[1100px] max-h-[85vh] bg-card border border-border rounded-lg flex flex-col overflow-hidden"
           style={{ boxShadow: '0 4px 60px rgba(0,0,0,0.7)' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-3">
            <span className="font-bold text-[14px] text-fg">{symbol}</span>
            <span className="text-[10px] text-ghost">OPTION CHAIN</span>
            {chain && <span className="num text-[11px] text-amber">Spot {fmt2(chain.spot_price)}</span>}
          </div>
          <div className="flex items-center gap-3">
            {/* Expiry selector */}
            {expiries.length > 0 && (
              <div className="seg-group">
                {expiries.slice(0, 4).map(exp => (
                  <button key={exp} onClick={() => setSelectedExp(exp)}
                    className={`seg-btn ${selectedExp === exp ? 'active' : ''}`}
                    style={selectedExp === exp ? { color: '#2d7ee8' } : undefined}>
                    {exp}
                  </button>
                ))}
              </div>
            )}
            <button onClick={onClose} className="text-ghost hover:text-fg text-sm px-2">✕</button>
          </div>
        </div>

        {/* Loading / Error */}
        {loading && <div className="flex-1 flex items-center justify-center text-[10px] text-ghost">Loading option chain…</div>}
        {error && <div className="flex-1 flex items-center justify-center text-[10px] text-bear">Error: {error}</div>}

        {/* Chain table */}
        {chain && !loading && (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-[10px] border-collapse">
              <thead className="sticky top-0 bg-panel z-10">
                <tr className="border-b border-border">
                  {/* Call side */}
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">OI</th>
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">VOL</th>
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">IV</th>
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">Δ</th>
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">BID</th>
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider">ASK</th>
                  <th className="px-2 py-2 text-right font-bold tracking-wider" style={{ color: '#0dbd7d' }}>CALL</th>
                  {/* Strike */}
                  <th className="px-3 py-2 text-center font-bold tracking-wider text-accent">STRIKE</th>
                  {/* Put side */}
                  <th className="px-2 py-2 text-left font-bold tracking-wider" style={{ color: '#f23d55' }}>PUT</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">BID</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">ASK</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">Δ</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">IV</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">VOL</th>
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider">OI</th>
                </tr>
              </thead>
              <tbody>
                {chain.strikes.map((s: OptionStrike) => {
                  const isATM = atmStrike != null && s.strike_price === atmStrike;
                  const itm_call = chain.spot_price > s.strike_price;
                  const itm_put  = chain.spot_price < s.strike_price;
                  return (
                    <tr key={s.strike_price}
                        className={`border-b border-border transition-colors ${isATM ? 'bg-accent/8' : 'hover:bg-lift'}`}>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtOI(s.call_oi)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtOI(s.call_volume)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-amber">{fmtIV(s.call_iv)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtGreek(s.call_delta)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmt2(s.call_bid)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmt2(s.call_ask)}</td>
                      <td className={`px-2 py-1.5 text-right num tabular-nums font-bold ${itm_call ? 'text-bull' : 'text-fg'}`}>
                        {fmt2(s.call_ltp)}
                      </td>
                      <td className={`px-3 py-1.5 text-center num tabular-nums font-bold ${isATM ? 'text-accent' : 'text-fg'}`}>
                        {s.strike_price}
                      </td>
                      <td className={`px-2 py-1.5 text-left num tabular-nums font-bold ${itm_put ? 'text-bear' : 'text-fg'}`}>
                        {fmt2(s.put_ltp)}
                      </td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-dim">{fmt2(s.put_bid)}</td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-dim">{fmt2(s.put_ask)}</td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-dim">{fmtGreek(s.put_delta)}</td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-amber">{fmtIV(s.put_iv)}</td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-dim">{fmtOI(s.put_volume)}</td>
                      <td className="px-2 py-1.5 text-left num tabular-nums text-dim">{fmtOI(s.put_oi)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
});

OptionChainPanel.displayName = 'OptionChainPanel';

function fmtOI(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1_00_000) return `${(v / 1_00_000).toFixed(1)}L`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

function fmtIV(v: number | null | undefined): string {
  return v != null ? `${v.toFixed(1)}%` : '—';
}

function fmtGreek(v: number | null | undefined): string {
  return v != null ? v.toFixed(2) : '—';
}
