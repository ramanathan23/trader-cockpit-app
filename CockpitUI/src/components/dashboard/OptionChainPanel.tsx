'use client';

import { memo, useEffect, useMemo, useState } from 'react';
import type { ExpiryListResponse, OptionChainResponse, OptionStrike } from '@/domain/option_chain';
import { fmt2 } from '@/lib/fmt';

interface OptionChainPanelProps {
  symbol: string;
  onClose: () => void;
  embedded?: boolean;
}

const ATM_COUNT = 5;

function assessChain(strikes: OptionStrike[], spotPrice: number): { label: string; color: string; reasons: string[] } {
  if (strikes.length === 0) return { label: 'No data', color: 'rgb(var(--ghost))', reasons: [] };

  const reasons: string[] = [];
  let score = 0;

  const ivs = strikes
    .map(strike => [strike.call_iv, strike.put_iv].filter((v): v is number => v != null && v > 0))
    .flat();
  const avgIV = ivs.length ? ivs.reduce((sum, value) => sum + value, 0) / ivs.length : 0;

  if (avgIV > 0) {
    if (avgIV < 25) {
      score += 1;
      reasons.push(`Low IV ${avgIV.toFixed(1)}%`);
    } else if (avgIV > 40) {
      score -= 1;
      reasons.push(`High IV ${avgIV.toFixed(1)}%`);
    } else {
      reasons.push(`Moderate IV ${avgIV.toFixed(1)}%`);
    }
  }

  const atm = strikes.reduce((best, strike) =>
    Math.abs(strike.strike_price - spotPrice) < Math.abs(best.strike_price - spotPrice) ? strike : best,
    strikes[0],
  );

  const spreads = [
    atm.call_ask != null && atm.call_bid != null && atm.call_bid > 0 ? (atm.call_ask - atm.call_bid) / atm.call_bid * 100 : null,
    atm.put_ask != null && atm.put_bid != null && atm.put_bid > 0 ? (atm.put_ask - atm.put_bid) / atm.put_bid * 100 : null,
  ].filter((value): value is number => value != null);

  if (spreads.length) {
    const spread = spreads.reduce((sum, value) => sum + value, 0) / spreads.length;
    if (spread < 1) score += 1;
    if (spread > 3) score -= 1;
    reasons.push(`Spread ${spread.toFixed(1)}%`);
  }

  const totalCallOI = strikes.reduce((sum, row) => sum + (row.call_oi ?? 0), 0);
  const totalPutOI = strikes.reduce((sum, row) => sum + (row.put_oi ?? 0), 0);
  const totalVolume = strikes.reduce((sum, row) => sum + (row.call_volume ?? 0) + (row.put_volume ?? 0), 0);

  if (totalCallOI + totalPutOI > 0) {
    const pcr = totalPutOI / (totalCallOI || 1);
    reasons.push(`PCR ${pcr.toFixed(2)}`);
    if (pcr > 1.2) score += 1;
    if (pcr < 0.7) score -= 1;
  }

  if (totalVolume === 0) {
    score -= 2;
    reasons.push('No traded volume');
  } else if (totalVolume < 1000) {
    reasons.push('Low volume');
  }

  return {
    label: score >= 2 ? 'Favourable for buying' : score >= 0 ? 'Neutral' : 'Unfavourable for buying',
    color: score >= 2 ? 'rgb(var(--bull))' : score >= 0 ? 'rgb(var(--amber))' : 'rgb(var(--bear))',
    reasons,
  };
}

export const OptionChainPanel = memo(({ symbol, onClose, embedded = false }: OptionChainPanelProps) => {
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExp, setSelectedExp] = useState<string | null>(null);
  const [chain, setChain] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch('/api/v1/optionchain/expiries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    })
      .then(response => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json();
      })
      .then((data: ExpiryListResponse) => {
        setExpiries(data.expiries);
        setSelectedExp(data.expiries[0] ?? null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (!selectedExp) return;
    setLoading(true);
    setError(null);
    fetch('/api/v1/optionchain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, expiry: selectedExp }),
    })
      .then(response => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json();
      })
      .then((data: OptionChainResponse) => setChain(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [symbol, selectedExp]);

  const atmStrike = useMemo(() => {
    if (!chain?.strikes.length) return null;
    return chain.strikes.reduce((best, strike) =>
      Math.abs(strike.strike_price - chain.spot_price) < Math.abs(best - chain.spot_price) ? strike.strike_price : best,
      chain.strikes[0].strike_price,
    );
  }, [chain]);

  const visibleStrikes = useMemo(() => {
    if (!chain || atmStrike == null) return [];
    const idx = chain.strikes.findIndex(strike => strike.strike_price === atmStrike);
    if (idx === -1) return chain.strikes;
    return chain.strikes.slice(Math.max(0, idx - ATM_COUNT), Math.min(chain.strikes.length, idx + ATM_COUNT + 1));
  }, [chain, atmStrike]);

  const assessment = useMemo(() => {
    if (!chain) return null;
    return assessChain(visibleStrikes, chain.spot_price);
  }, [chain, visibleStrikes]);

  const tableContent = (
    <>
      {assessment && !loading && (
        <div className="flex flex-wrap items-center gap-3 border-b border-border bg-base/35 px-4 py-2 text-[11px]">
          <span className="font-black" style={{ color: assessment.color }}>{assessment.label}</span>
          {assessment.reasons.map(reason => <span key={reason} className="text-ghost">{reason}</span>)}
        </div>
      )}

      {loading && <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading option chain</div>}
      {error && !loading && <div className="flex flex-1 items-center justify-center text-[13px] text-bear">Error: {error}</div>}

      {chain && !loading && !error && (
        <div className="table-wrap flex-1">
          <table className="data-table text-[11px]">
            <thead>
              <tr>
                <th colSpan={7} className="text-right" style={{ color: 'rgb(var(--bull))' }}>Calls</th>
                <th className="text-center" style={{ color: 'rgb(var(--accent))' }}>Strike</th>
                <th colSpan={7} className="text-left" style={{ color: 'rgb(var(--bear))' }}>Puts</th>
              </tr>
              <tr>
                {['OI', 'Vol', 'IV', 'Delta', 'Bid', 'Ask', 'LTP'].map(h => <th key={`c-${h}`} className="text-right">{h}</th>)}
                <th className="text-center">Strike</th>
                {['LTP', 'Bid', 'Ask', 'Delta', 'IV', 'Vol', 'OI'].map(h => <th key={`p-${h}`} className="text-left">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {visibleStrikes.map(strike => {
                const isATM = atmStrike != null && strike.strike_price === atmStrike;
                const itmCall = chain.spot_price > strike.strike_price;
                const itmPut = chain.spot_price < strike.strike_price;
                return (
                  <tr key={strike.strike_price} className={isATM ? 'bg-accent/10' : ''}>
                    <td className="text-right num text-dim">{fmtOI(strike.call_oi)}</td>
                    <td className="text-right num text-dim">{fmtOI(strike.call_volume)}</td>
                    <td className="text-right num text-amber">{fmtIV(strike.call_iv)}</td>
                    <td className="text-right num text-dim">{fmtGreek(strike.call_delta)}</td>
                    <td className="text-right num text-dim">{fmt2(strike.call_bid)}</td>
                    <td className="text-right num text-dim">{fmt2(strike.call_ask)}</td>
                    <td className="text-right num font-black" style={{ color: itmCall ? 'rgb(var(--bull))' : 'rgb(var(--fg))' }}>{fmt2(strike.call_ltp)}</td>
                    <td className="text-center num font-black" style={{ color: isATM ? 'rgb(var(--accent))' : 'rgb(var(--fg))' }}>
                      {strike.strike_price}{isATM ? ' ATM' : ''}
                    </td>
                    <td className="text-left num font-black" style={{ color: itmPut ? 'rgb(var(--bear))' : 'rgb(var(--fg))' }}>{fmt2(strike.put_ltp)}</td>
                    <td className="text-left num text-dim">{fmt2(strike.put_bid)}</td>
                    <td className="text-left num text-dim">{fmt2(strike.put_ask)}</td>
                    <td className="text-left num text-dim">{fmtGreek(strike.put_delta)}</td>
                    <td className="text-left num text-amber">{fmtIV(strike.put_iv)}</td>
                    <td className="text-left num text-dim">{fmtOI(strike.put_volume)}</td>
                    <td className="text-left num text-dim">{fmtOI(strike.put_oi)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );

  if (embedded) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border px-4 py-2">
          {chain && <span className="chip num" style={{ color: 'rgb(var(--accent))' }}>Spot {fmt2(chain.spot_price)}</span>}
          {expiries.length > 0 && (
            <div className="seg-group">
              {expiries.slice(0, 4).map(expiry => (
                <button
                  key={expiry}
                  type="button"
                  onClick={() => setSelectedExp(expiry)}
                  className={`seg-btn ${selectedExp === expiry ? 'active' : ''}`}
                  style={selectedExp === expiry ? { color: 'rgb(var(--accent))' } : undefined}
                >
                  {expiry}
                </button>
              ))}
            </div>
          )}
        </div>
        {tableContent}
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="surface-card flex max-h-[88vh] w-[96vw] max-w-[1160px] flex-col overflow-hidden"
        onClick={event => event.stopPropagation()}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            <span className="text-[10px] font-black uppercase text-ghost">Option chain</span>
            {chain && <span className="chip num" style={{ color: 'rgb(var(--accent))' }}>Spot {fmt2(chain.spot_price)}</span>}
          </div>

          <div className="flex items-center gap-2">
            {expiries.length > 0 && (
              <div className="seg-group">
                {expiries.slice(0, 4).map(expiry => (
                  <button
                    key={expiry}
                    type="button"
                    onClick={() => setSelectedExp(expiry)}
                    className={`seg-btn ${selectedExp === expiry ? 'active' : ''}`}
                    style={selectedExp === expiry ? { color: 'rgb(var(--accent))' } : undefined}
                  >
                    {expiry}
                  </button>
                ))}
              </div>
            )}
            <button type="button" onClick={onClose} className="icon-btn" title="Close" aria-label="Close">x</button>
          </div>
        </div>
        {tableContent}
      </div>
    </div>
  );
});

OptionChainPanel.displayName = 'OptionChainPanel';

function fmtOI(v: number | null | undefined): string {
  if (v == null) return '-';
  if (v >= 100_000) return `${(v / 100_000).toFixed(1)}L`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

function fmtIV(v: number | null | undefined): string {
  return v != null ? `${v.toFixed(1)}%` : '-';
}

function fmtGreek(v: number | null | undefined): string {
  return v != null ? v.toFixed(2) : '-';
}
