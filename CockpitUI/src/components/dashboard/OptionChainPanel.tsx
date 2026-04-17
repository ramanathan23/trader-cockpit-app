'use client';

import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import type { ExpiryListResponse, OptionChainResponse, OptionStrike } from '@/domain/option_chain';
import type { ScoredSymbol } from '@/domain/dashboard';
import { fmt2 } from '@/lib/fmt';

interface OptionChainPanelProps {
  symbol: string;
  onClose: () => void;
  scoreData?: ScoredSymbol | null;
}

const ATM_COUNT = 5; // strikes above + below ATM

/** Quick assessment of option chain health for buying.
 *  IV is correlated with price momentum & structure — high IV alone
 *  is not unfavourable if the stock is coiling or has strong trend support. */
function assessChain(
  strikes: OptionStrike[],
  spotPrice: number,
  scoreData?: ScoredSymbol | null,
  oiData?: OIAnalysis | null,
): { label: string; color: string; reasons: string[] } {
  if (strikes.length === 0) return { label: 'No data', color: 'text-ghost', reasons: [] };

  const reasons: string[] = [];
  let score = 0; // -3 … +3

  // Momentum / structure context from unified scorer
  const rsi        = scoreData?.rsi_14 ?? null;
  const momScore   = scoreData?.momentum_score ?? null;
  const trendScore = scoreData?.trend_score ?? null;
  const volScore   = scoreData?.volatility_score ?? null;
  const squeeze    = scoreData?.bb_squeeze === true;
  const nr7        = scoreData?.nr7 === true;

  const isOverextended   = (rsi != null && rsi > 75) || (momScore != null && momScore > 80);
  const isCoiling        = squeeze || nr7 || (volScore != null && volScore >= 65);
  const hasStrongTrend   = (trendScore != null && trendScore >= 60) && (rsi == null || rsi < 72);
  const hasMomentum      = (momScore != null && momScore >= 60) || (trendScore != null && trendScore >= 65);

  // 1. IV level (avg of ATM CE + PE) — correlated with price context
  const atmIVs = strikes
    .filter(s => s.call_iv != null || s.put_iv != null)
    .map(s => ((s.call_iv ?? 0) + (s.put_iv ?? 0)) / ((s.call_iv != null ? 1 : 0) + (s.put_iv != null ? 1 : 0)))
    .filter(v => v > 0);
  const avgIV = atmIVs.length ? atmIVs.reduce((a, b) => a + b, 0) / atmIVs.length : 0;

  if (avgIV > 0) {
    if (avgIV < 25) {
      score += 1;
      reasons.push(`Low IV ${avgIV.toFixed(1)}% — premiums cheap`);
    } else if (avgIV < 40) {
      // Moderate IV — momentum context matters
      if (isOverextended) {
        score -= 1;
        reasons.push(`Moderate IV ${avgIV.toFixed(1)}% + overextended (RSI ${rsi?.toFixed(0) ?? '?'}) — risky`);
      } else if (hasMomentum) {
        score += 1;
        reasons.push(`Moderate IV ${avgIV.toFixed(1)}% + momentum backing — justified`);
      } else {
        reasons.push(`Moderate IV ${avgIV.toFixed(1)}%`);
      }
    } else {
      // High IV — not automatically bad; correlate with price context
      if (isOverextended) {
        score -= 2;
        reasons.push(`High IV ${avgIV.toFixed(1)}% + overextended (RSI ${rsi?.toFixed(0) ?? '?'}) — premium crush risk`);
      } else if (isCoiling) {
        // Sideways / compressed — IV justified by upcoming expansion potential
        reasons.push(`High IV ${avgIV.toFixed(1)}% but coiling${squeeze ? ' (squeeze)' : ''}${nr7 ? ' (NR7)' : ''} — breakout potential`);
      } else if (hasStrongTrend) {
        reasons.push(`High IV ${avgIV.toFixed(1)}% but trending strongly — directional play`);
      } else {
        score -= 1;
        reasons.push(`High IV ${avgIV.toFixed(1)}% — premiums expensive`);
      }
    }
  }

  // 2. Bid-Ask spread on ATM
  const atm = strikes.reduce((best, s) =>
    Math.abs(s.strike_price - spotPrice) < Math.abs(best.strike_price - spotPrice) ? s : best,
    strikes[0],
  );
  const callSpread = (atm.call_ask != null && atm.call_bid != null && atm.call_bid > 0)
    ? ((atm.call_ask - atm.call_bid) / atm.call_bid) * 100 : null;
  const putSpread  = (atm.put_ask != null && atm.put_bid != null && atm.put_bid > 0)
    ? ((atm.put_ask - atm.put_bid) / atm.put_bid) * 100 : null;
  const avgSpread  = [callSpread, putSpread].filter((v): v is number => v != null);
  if (avgSpread.length) {
    const spread = avgSpread.reduce((a, b) => a + b, 0) / avgSpread.length;
    if (spread < 1) { score += 1; reasons.push(`Tight spread ${spread.toFixed(1)}%`); }
    else if (spread > 3) { score -= 1; reasons.push(`Wide spread ${spread.toFixed(1)}% — slippage risk`); }
    else { reasons.push(`Spread ${spread.toFixed(1)}%`); }
  }

  // 3. OI & volume (liquidity)
  const totalCallOI = strikes.reduce((s, r) => s + (r.call_oi ?? 0), 0);
  const totalPutOI  = strikes.reduce((s, r) => s + (r.put_oi ?? 0), 0);
  const totalVol    = strikes.reduce((s, r) => s + (r.call_volume ?? 0) + (r.put_volume ?? 0), 0);

  if (totalCallOI + totalPutOI > 0) {
    const pcr = totalPutOI / (totalCallOI || 1);
    reasons.push(`PCR ${pcr.toFixed(2)}`);
    if (pcr > 1.2) { score += 1; reasons.push('Bullish OI skew'); }
    else if (pcr < 0.7) { score -= 1; reasons.push('Bearish OI skew'); }
  }

  if (totalVol === 0) { score -= 2; reasons.push('No volume — illiquid'); }
  else if (totalVol < 1000) { reasons.push('Low volume'); }

  // 4. OI behaviour — manipulation / bias from full-chain analysis
  if (oiData) {
    if (oiData.manipulation) {
      score -= 2;
      reasons.push('OI manipulation detected — stay away');
    }
    if (oiData.bias === 'SIDEWAYS') {
      reasons.push('OI walls suggest range-bound — directional bets risky');
    }
  }

  const label = score >= 2 ? 'Favourable for buying' : score >= 0 ? 'Neutral' : 'Unfavourable for buying';
  const color = score >= 2 ? 'text-bull' : score >= 0 ? 'text-amber' : 'text-bear';
  return { label, color, reasons };
}

// ── OI behaviour analysis ────────────────────────────────────────────────────

interface OIAnalysis {
  pcr:              number;
  pcrLabel:         string;   // "Bullish" | "Bearish" | "Neutral"
  pcrColor:         string;
  bias:             string;   // "BULL" | "BEAR" | "SIDEWAYS" | "CONTESTED"
  biasColor:        string;
  biasReason:       string;
  unusualStrikes:   string[]; // e.g. "CE 24500 OI 12L (3.2× avg)"
  manipulation:     boolean;
  manipReason:      string | null;
  maxPainStrike:    number | null;
}

function analyzeOI(strikes: OptionStrike[], spotPrice: number): OIAnalysis | null {
  if (strikes.length === 0) return null;

  const totalCallOI = strikes.reduce((s, r) => s + (r.call_oi ?? 0), 0);
  const totalPutOI  = strikes.reduce((s, r) => s + (r.put_oi ?? 0), 0);
  const totalCallVol = strikes.reduce((s, r) => s + (r.call_volume ?? 0), 0);
  const totalPutVol  = strikes.reduce((s, r) => s + (r.put_volume ?? 0), 0);

  if (totalCallOI + totalPutOI === 0) return null;

  // ── PCR ──
  const pcr = totalPutOI / (totalCallOI || 1);
  let pcrLabel: string;
  let pcrColor: string;
  if (pcr > 1.2)      { pcrLabel = 'Bullish';  pcrColor = 'text-bull'; }
  else if (pcr < 0.7) { pcrLabel = 'Bearish';  pcrColor = 'text-bear'; }
  else                 { pcrLabel = 'Neutral';  pcrColor = 'text-amber'; }

  // ── Dominant OI walls (find where the real walls are) ──
  const callsByOI = [...strikes].filter(s => (s.call_oi ?? 0) > 0)
    .sort((a, b) => (b.call_oi ?? 0) - (a.call_oi ?? 0));
  const putsByOI = [...strikes].filter(s => (s.put_oi ?? 0) > 0)
    .sort((a, b) => (b.put_oi ?? 0) - (a.put_oi ?? 0));

  const topCallWall = callsByOI[0]?.strike_price ?? null;  // Resistance
  const topPutWall  = putsByOI[0]?.strike_price ?? null;   // Support

  // ── Directional bias from OI structure ──
  let bias: string;
  let biasColor: string;
  let biasReason: string;

  if (topCallWall != null && topPutWall != null) {
    const callWallDist = topCallWall - spotPrice;  // positive = above spot
    const putWallDist  = spotPrice - topPutWall;    // positive = below spot

    if (pcr > 1.2 && putWallDist > callWallDist * 0.6) {
      // Strong put writing below → support holds → bullish
      bias = 'BULL'; biasColor = 'text-bull';
      biasReason = `Put wall ${topPutWall} supports upside, PCR ${pcr.toFixed(2)}`;
    } else if (pcr < 0.7 && callWallDist > putWallDist * 0.6) {
      // Heavy call writing above → resistance → bearish
      bias = 'BEAR'; biasColor = 'text-bear';
      biasReason = `Call wall ${topCallWall} caps upside, PCR ${pcr.toFixed(2)}`;
    } else if (callWallDist < spotPrice * 0.01 && putWallDist < spotPrice * 0.01) {
      // Both walls very close to spot → range-bound
      bias = 'SIDEWAYS'; biasColor = 'text-amber';
      biasReason = `Walls tight: Put ${topPutWall} / Call ${topCallWall} — range-bound`;
    } else if (pcr >= 0.7 && pcr <= 1.2) {
      bias = 'CONTESTED'; biasColor = 'text-amber';
      biasReason = `Balanced OI — no clear directional edge`;
    } else {
      bias = pcr > 1.0 ? 'BULL' : 'BEAR';
      biasColor = pcr > 1.0 ? 'text-bull' : 'text-bear';
      biasReason = `PCR ${pcr.toFixed(2)} with wall spread ${topPutWall}–${topCallWall}`;
    }
  } else {
    bias = 'CONTESTED'; biasColor = 'text-dim';
    biasReason = 'Insufficient OI data';
  }

  // ── Unusual OI concentration (strike OI > 2.5× average) ──
  const avgCallOI = totalCallOI / strikes.length;
  const avgPutOI  = totalPutOI / strikes.length;
  const unusualStrikes: string[] = [];

  for (const s of strikes) {
    if ((s.call_oi ?? 0) > avgCallOI * 2.5 && avgCallOI > 0) {
      const mult = (s.call_oi ?? 0) / avgCallOI;
      unusualStrikes.push(`CE ${s.strike_price} OI ${fmtOI(s.call_oi)} (${mult.toFixed(1)}× avg)`);
    }
    if ((s.put_oi ?? 0) > avgPutOI * 2.5 && avgPutOI > 0) {
      const mult = (s.put_oi ?? 0) / avgPutOI;
      unusualStrikes.push(`PE ${s.strike_price} OI ${fmtOI(s.put_oi)} (${mult.toFixed(1)}× avg)`);
    }
  }

  // ── Manipulation detection ──
  // When both CE and PE OI build on the same side of spot (same strikes),
  // or volume is extremely one-sided vs OI direction → synthetic pinning / manipulation.
  let manipulation = false;
  let manipReason: string | null = null;

  // Check 1: Heavy writing on BOTH sides of ATM (±2 strikes) — synthetic pinning
  const nearATM = strikes.filter(s =>
    Math.abs(s.strike_price - spotPrice) <= (strikes.length >= 2
      ? Math.abs(strikes[1].strike_price - strikes[0].strike_price) * 2
      : spotPrice * 0.03),
  );
  const nearCallOI = nearATM.reduce((s, r) => s + (r.call_oi ?? 0), 0);
  const nearPutOI  = nearATM.reduce((s, r) => s + (r.put_oi ?? 0), 0);
  const nearRatio   = nearCallOI > 0 && nearPutOI > 0
    ? Math.min(nearCallOI, nearPutOI) / Math.max(nearCallOI, nearPutOI)
    : 0;

  if (nearRatio > 0.75 && (nearCallOI + nearPutOI) > (totalCallOI + totalPutOI) * 0.5) {
    // Nearly equal CE+PE writing concentrated at ATM with both sides heavy
    manipulation = true;
    manipReason = `Equal CE+PE walls at ATM (${nearRatio.toFixed(0)}% balanced, ${((nearCallOI + nearPutOI) / (totalCallOI + totalPutOI) * 100).toFixed(0)}% of total OI) — likely pinning`;
  }

  // Check 2: Volume divergence from OI direction
  // If OI says bullish (high PCR) but call volume >>> put volume → smart money loading calls
  // while retail writes puts → fine. BUT if PCR bullish and put volume >>> call volume,
  // the "support" is new shorts added (panic) not conviction — bearish trap.
  if (!manipulation && totalCallVol + totalPutVol > 0) {
    const volPCR = totalPutVol / (totalCallVol || 1);
    if (pcr > 1.2 && volPCR > 2.0) {
      manipulation = true;
      manipReason = `PCR bullish (${pcr.toFixed(2)}) but today's put volume ${fmtOI(totalPutVol)} >>> call volume ${fmtOI(totalCallVol)} — fresh put selling may be a trap`;
    } else if (pcr < 0.7 && volPCR < 0.4) {
      manipulation = true;
      manipReason = `PCR bearish (${pcr.toFixed(2)}) but today's call volume ${fmtOI(totalCallVol)} >>> put volume ${fmtOI(totalPutVol)} — call writing may be a trap`;
    }
  }

  // ── Max pain estimate (strike where total OI obligation is minimized) ──
  let maxPainStrike: number | null = null;
  let minPain = Infinity;
  for (const s of strikes) {
    let pain = 0;
    for (const r of strikes) {
      const callPain = Math.max(0, s.strike_price - r.strike_price) * (r.call_oi ?? 0);
      const putPain  = Math.max(0, r.strike_price - s.strike_price) * (r.put_oi ?? 0);
      pain += callPain + putPain;
    }
    if (pain < minPain) { minPain = pain; maxPainStrike = s.strike_price; }
  }

  return { pcr, pcrLabel, pcrColor, bias, biasColor, biasReason, unusualStrikes, manipulation, manipReason, maxPainStrike };
}

export const OptionChainPanel = memo(({ symbol, onClose, scoreData }: OptionChainPanelProps) => {
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

/** Compute risk:reward for a 2% underlying stop-loss.
 *  Risk  = |delta| × 2% × spot, capped at premium paid.
 *  R:R   = premium / risk — multiples of SL-risk your entry represents. */
function computeRR(delta: number | null, ltp: number | null, spotPrice: number): { rr: number | null; risk: number | null } {
  if (delta == null || ltp == null || ltp <= 0 || spotPrice <= 0) return { rr: null, risk: null };
  const absDelta = Math.abs(delta);
  if (absDelta === 0) return { rr: null, risk: null };
  const slLoss = absDelta * 0.02 * spotPrice;
  const risk = Math.min(slLoss, ltp);
  return { rr: ltp / risk, risk };
}

function fmtRR(rr: number | null): string {
  return rr != null ? `${rr.toFixed(1)}` : '—';
}

function rrColor(rr: number | null): string {
  if (rr == null) return 'text-dim';
  if (rr >= 2.0) return 'text-bull';
  if (rr >= 1.2) return 'text-amber';
  return 'text-bear';
}
