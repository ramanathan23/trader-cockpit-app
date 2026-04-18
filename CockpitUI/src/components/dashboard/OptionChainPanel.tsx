'use client';

import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import type { ExpiryListResponse, OptionChainResponse, OptionStrike } from '@/domain/option_chain';
import type { ScoredSymbol } from '@/domain/dashboard';
import { fmt2 } from '@/lib/fmt';
import { LIVE_FEED } from '@/lib/api-config';
import {
  type OIAnalysis,
  assessChain,
  analyzeOI,
  computeRR,
  fmtOI,
  fmtIV,
  fmtGreek,
  fmtRR,
  rrColor,
} from '@/lib/option-chain-analysis';

interface OptionChainPanelProps {
  symbol: string;
  onClose: () => void;
  scoreData?: ScoredSymbol | null;
}

const ATM_COUNT = 5; // strikes above + below ATM

export const OptionChainPanel = memo(({ symbol, onClose, scoreData }: OptionChainPanelProps) => {
  const [expiries,     setExpiries]     = useState<string[]>([]);
  const [selectedExp,  setSelectedExp]  = useState<string | null>(null);
  const [chain,        setChain]        = useState<OptionChainResponse | null>(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);

  // Load expiries on mount
  useEffect(() => {
    setLoading(true);
    fetch(LIVE_FEED.OPTION_CHAIN_EXPIRIES, {
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
    fetch(LIVE_FEED.OPTION_CHAIN, {
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

  // Only show ATM_COUNT strikes above & below ATM
  const visibleStrikes = useMemo(() => {
    if (!chain || atmStrike == null) return [];
    const idx = chain.strikes.findIndex(s => s.strike_price === atmStrike);
    if (idx === -1) return chain.strikes;
    const lo = Math.max(0, idx - ATM_COUNT);
    const hi = Math.min(chain.strikes.length, idx + ATM_COUNT + 1);
    return chain.strikes.slice(lo, hi);
  }, [chain, atmStrike]);

  const oiAnalysis = useMemo(() => {
    if (!chain) return null;
    return analyzeOI(chain.strikes, chain.spot_price);
  }, [chain]);

  const assessment = useMemo(() => {
    if (!chain) return null;
    return assessChain(visibleStrikes, chain.spot_price, scoreData, oiAnalysis);
  }, [chain, visibleStrikes, scoreData, oiAnalysis]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,12,24,0.88)' }} onClick={onClose}>
      <div className="w-[95vw] max-w-[1200px] max-h-[85vh] bg-card border border-border rounded-lg flex flex-col overflow-hidden"
           style={{ boxShadow: '0 4px 60px rgba(0,0,0,0.7)' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-3">
            <span className="font-bold text-[14px] text-fg">{symbol}</span>
            <span className="text-[10px] text-ghost">OPTION CHAIN</span>
            {chain && (
              <span className="num text-[12px] font-bold px-2 py-0.5 rounded"
                    style={{ background: 'rgba(45,126,232,0.15)', color: '#2d7ee8' }}>
                Spot {fmt2(chain.spot_price)}
              </span>
            )}
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

        {/* Assessment bar */}
        {assessment && !loading && (
          <div className="px-4 py-2 border-b border-border flex items-center gap-4 text-[10px]">
            <span className={`font-bold text-[11px] ${assessment.color}`}>{assessment.label}</span>
            {assessment.reasons.map((r, i) => (
              <span key={i} className="text-ghost">• {r}</span>
            ))}
          </div>
        )}

        {/* OI Analysis bar */}
        {oiAnalysis && !loading && (
          <div className="px-4 py-2 border-b border-border flex flex-col gap-1.5 text-[10px]">
            {/* Row 1: PCR + Bias + Max Pain + Manipulation warning */}
            <div className="flex items-center gap-5">
              <span className="flex items-center gap-1.5">
                <span className="text-ghost font-bold">PCR</span>
                <span className={`font-bold ${oiAnalysis.pcrColor}`}>{oiAnalysis.pcr.toFixed(2)}</span>
                <span className={`text-[9px] ${oiAnalysis.pcrColor}`}>{oiAnalysis.pcrLabel}</span>
              </span>
              <span className="text-border">│</span>
              <span className="flex items-center gap-1.5">
                <span className="text-ghost font-bold">Bias</span>
                <span className={`font-bold px-1.5 py-0.5 rounded text-[9px] ${oiAnalysis.biasColor}`}
                      style={{ background: oiAnalysis.bias === 'BULL' ? 'rgba(13,189,125,0.12)' : oiAnalysis.bias === 'BEAR' ? 'rgba(242,61,85,0.12)' : 'rgba(251,191,36,0.12)' }}>
                  {oiAnalysis.bias}
                </span>
                <span className="text-ghost">{oiAnalysis.biasReason}</span>
              </span>
              {oiAnalysis.maxPainStrike != null && (
                <>
                  <span className="text-border">│</span>
                  <span className="flex items-center gap-1.5">
                    <span className="text-ghost font-bold">Max Pain</span>
                    <span className="text-accent font-bold">{oiAnalysis.maxPainStrike}</span>
                  </span>
                </>
              )}
              {oiAnalysis.manipulation && (
                <>
                  <span className="text-border">│</span>
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ background: 'rgba(242,61,85,0.15)' }}>
                    <span className="text-bear font-bold">⚠ CAUTION</span>
                    <span className="text-bear">{oiAnalysis.manipReason}</span>
                  </span>
                </>
              )}
            </div>
            {/* Row 2: Unusual OI strikes */}
            {oiAnalysis.unusualStrikes.length > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-ghost font-bold">Unusual OI</span>
                {oiAnalysis.unusualStrikes.slice(0, 6).map((s, i) => (
                  <span key={i} className="text-amber">• {s}</span>
                ))}
              </div>
            )}
          </div>
        )}

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
                  <th className="px-2 py-2 text-right text-ghost font-bold tracking-wider" title="R:R at 2% underlying SL">R:R</th>
                  {/* Strike */}
                  <th className="px-3 py-2 text-center font-bold tracking-wider text-accent">STRIKE</th>
                  {/* Put side */}
                  <th className="px-2 py-2 text-left text-ghost font-bold tracking-wider" title="R:R at 2% underlying SL">R:R</th>
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
                {visibleStrikes.map((s: OptionStrike) => {
                  const isATM = atmStrike != null && s.strike_price === atmStrike;
                  const itm_call = chain.spot_price > s.strike_price;
                  const itm_put  = chain.spot_price < s.strike_price;
                  const callRR = computeRR(s.call_delta, s.call_ltp, chain.spot_price);
                  const putRR  = computeRR(s.put_delta, s.put_ltp, chain.spot_price);
                  return (
                    <tr key={s.strike_price}
                        className={`border-b border-border transition-colors ${isATM ? 'ring-1 ring-accent/50' : 'hover:bg-lift'}`}
                        style={isATM ? { background: 'rgba(45,126,232,0.12)' } : undefined}>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtOI(s.call_oi)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtOI(s.call_volume)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-amber">{fmtIV(s.call_iv)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmtGreek(s.call_delta)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmt2(s.call_bid)}</td>
                      <td className="px-2 py-1.5 text-right num tabular-nums text-dim">{fmt2(s.call_ask)}</td>
                      <td className={`px-2 py-1.5 text-right num tabular-nums font-bold ${itm_call ? 'text-bull' : 'text-fg'}`}>
                        {fmt2(s.call_ltp)}
                      </td>
                      <td className={`px-2 py-1.5 text-right num tabular-nums font-bold ${rrColor(callRR.rr)}`}
                          title={callRR.risk != null ? `Risk ₹${callRR.risk.toFixed(1)} on 2% SL` : undefined}>
                        {fmtRR(callRR.rr)}
                      </td>
                      <td className={`px-3 py-1.5 text-center num tabular-nums font-bold ${isATM ? 'text-accent' : 'text-fg'}`}>
                        {s.strike_price}
                        {isATM && <span className="ml-1 text-[8px] text-accent font-normal">ATM</span>}
                      </td>
                      <td className={`px-2 py-1.5 text-left num tabular-nums font-bold ${rrColor(putRR.rr)}`}
                          title={putRR.risk != null ? `Risk ₹${putRR.risk.toFixed(1)} on 2% SL` : undefined}>
                        {fmtRR(putRR.rr)}
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
