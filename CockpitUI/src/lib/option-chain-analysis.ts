import type { OptionStrike } from '@/domain/option_chain';
import type { ScoredSymbol } from '@/domain/dashboard';

// ── Types ────────────────────────────────────────────────────────────────────

export interface OIAnalysis {
  pcr:              number;
  pcrLabel:         string;
  pcrColor:         string;
  bias:             string;
  biasColor:        string;
  biasReason:       string;
  unusualStrikes:   string[];
  manipulation:     boolean;
  manipReason:      string | null;
  maxPainStrike:    number | null;
}

export interface ChainAssessment {
  label: string;
  color: string;
  reasons: string[];
}

// ── Formatting helpers ───────────────────────────────────────────────────────

export function fmtOI(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1_00_000) return `${(v / 1_00_000).toFixed(1)}L`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

export function fmtIV(v: number | null | undefined): string {
  return v != null ? `${v.toFixed(1)}%` : '—';
}

export function fmtGreek(v: number | null | undefined): string {
  return v != null ? v.toFixed(2) : '—';
}

/** Risk:reward for a 2% underlying stop-loss.
 *  Risk  = |delta| × 2% × spot, capped at premium paid.
 *  R:R   = premium / risk. */
export function computeRR(
  delta: number | null,
  ltp: number | null,
  spotPrice: number,
): { rr: number | null; risk: number | null } {
  if (delta == null || ltp == null || ltp <= 0 || spotPrice <= 0) return { rr: null, risk: null };
  const absDelta = Math.abs(delta);
  if (absDelta === 0) return { rr: null, risk: null };
  const slLoss = absDelta * 0.02 * spotPrice;
  const risk = Math.min(slLoss, ltp);
  return { rr: ltp / risk, risk };
}

export function fmtRR(rr: number | null): string {
  return rr != null ? `${rr.toFixed(1)}` : '—';
}

export function rrColor(rr: number | null): string {
  if (rr == null) return 'text-dim';
  if (rr >= 2.0) return 'text-bull';
  if (rr >= 1.2) return 'text-amber';
  return 'text-bear';
}

// ── Chain quality assessment ─────────────────────────────────────────────────

/** Intraday / BTST option chain assessment.
 *  Prioritises LIQUIDITY (spread + volume) over IV.
 *  High IV = bigger premium moves = good for directional intraday buys.
 *  OI gives directional colour, not a gate. Only hard blockers:
 *  zero volume, wide spreads, manipulation. */
export function assessChain(
  strikes: OptionStrike[],
  spotPrice: number,
  scoreData?: ScoredSymbol | null,
  oiData?: OIAnalysis | null,
): ChainAssessment {
  if (strikes.length === 0) return { label: 'No data', color: 'text-ghost', reasons: [] };

  const reasons: string[] = [];
  let score = 0;

  const momScore   = scoreData?.momentum_score ?? null;
  const trendScore = scoreData?.trend_score ?? null;
  const hasMomentum = (momScore != null && momScore >= 60) || (trendScore != null && trendScore >= 65);

  // 1. IV — informational for intraday
  const atmIVs = strikes
    .filter(s => s.call_iv != null || s.put_iv != null)
    .map(s => ((s.call_iv ?? 0) + (s.put_iv ?? 0)) / ((s.call_iv != null ? 1 : 0) + (s.put_iv != null ? 1 : 0)))
    .filter(v => v > 0);
  const avgIV = atmIVs.length ? atmIVs.reduce((a, b) => a + b, 0) / atmIVs.length : 0;

  if (avgIV > 0) {
    if (avgIV < 20) {
      reasons.push(`Low IV ${avgIV.toFixed(1)}% — small premium moves, need big stock move`);
    } else if (avgIV < 40) {
      reasons.push(`IV ${avgIV.toFixed(1)}% — normal range`);
    } else if (avgIV < 60) {
      reasons.push(`IV ${avgIV.toFixed(1)}% — good premium movement for intraday`);
    } else {
      if (hasMomentum) {
        reasons.push(`High IV ${avgIV.toFixed(1)}% + momentum — premium moves fast, ride it`);
      } else {
        score -= 1;
        reasons.push(`Very high IV ${avgIV.toFixed(1)}% no momentum — IV crush risk if event-driven`);
      }
    }
  }

  // 2. Bid-Ask spread — CRITICAL for intraday
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
    if (spread < 1.5) { score += 1; reasons.push(`Tight spread ${spread.toFixed(1)}% — clean entry/exit`); }
    else if (spread > 5) { score -= 2; reasons.push(`Wide spread ${spread.toFixed(1)}% — slippage will eat profits`); }
    else if (spread > 3) { score -= 1; reasons.push(`Spread ${spread.toFixed(1)}% — factor slippage into target`); }
    else { reasons.push(`Spread ${spread.toFixed(1)}%`); }
  }

  // 3. Volume — CRITICAL
  const totalCallOI = strikes.reduce((s, r) => s + (r.call_oi ?? 0), 0);
  const totalPutOI  = strikes.reduce((s, r) => s + (r.put_oi ?? 0), 0);
  const totalVol    = strikes.reduce((s, r) => s + (r.call_volume ?? 0) + (r.put_volume ?? 0), 0);

  if (totalVol === 0) { score -= 2; reasons.push('Zero volume — cannot trade'); }
  else if (totalVol < 500) { score -= 1; reasons.push(`Low volume ${totalVol} — tough to get fills`); }
  else if (totalVol > 10000) { score += 1; reasons.push(`Good volume ${(totalVol / 1000).toFixed(0)}K — liquid`); }
  else { reasons.push(`Volume ${(totalVol / 1000).toFixed(1)}K`); }

  // 4. OI — directional colour (informational, not gating)
  if (totalCallOI + totalPutOI > 0) {
    const pcr = totalPutOI / (totalCallOI || 1);
    if (pcr > 1.2) { reasons.push(`PCR ${pcr.toFixed(2)} — put writers supporting, CE buys have tailwind`); }
    else if (pcr < 0.7) { reasons.push(`PCR ${pcr.toFixed(2)} — call writers dominating, PE buys have tailwind`); }
    else { reasons.push(`PCR ${pcr.toFixed(2)} — balanced`); }
  }

  // 5. OI manipulation — hard blocker
  if (oiData) {
    if (oiData.manipulation) {
      score -= 2;
      reasons.push('OI manipulation detected — avoid');
    }
    if (oiData.bias === 'SIDEWAYS') {
      reasons.push('OI walls suggest range — play within walls or wait for break');
    }
  }

  const label = score >= 1 ? 'Tradeable — go' : score >= -1 ? 'Tradeable with caution' : 'Avoid — poor liquidity';
  const color = score >= 1 ? 'text-bull' : score >= -1 ? 'text-amber' : 'text-bear';
  return { label, color, reasons };
}

// ── OI behaviour analysis ────────────────────────────────────────────────────

export function analyzeOI(strikes: OptionStrike[], spotPrice: number): OIAnalysis | null {
  if (strikes.length === 0) return null;

  const totalCallOI = strikes.reduce((s, r) => s + (r.call_oi ?? 0), 0);
  const totalPutOI  = strikes.reduce((s, r) => s + (r.put_oi ?? 0), 0);
  const totalCallVol = strikes.reduce((s, r) => s + (r.call_volume ?? 0), 0);
  const totalPutVol  = strikes.reduce((s, r) => s + (r.put_volume ?? 0), 0);

  if (totalCallOI + totalPutOI === 0) return null;

  // PCR
  const pcr = totalPutOI / (totalCallOI || 1);
  let pcrLabel: string;
  let pcrColor: string;
  if (pcr > 1.2)      { pcrLabel = 'Bullish';  pcrColor = 'text-bull'; }
  else if (pcr < 0.7) { pcrLabel = 'Bearish';  pcrColor = 'text-bear'; }
  else                 { pcrLabel = 'Neutral';  pcrColor = 'text-amber'; }

  // Dominant OI walls
  const callsByOI = [...strikes].filter(s => (s.call_oi ?? 0) > 0)
    .sort((a, b) => (b.call_oi ?? 0) - (a.call_oi ?? 0));
  const putsByOI = [...strikes].filter(s => (s.put_oi ?? 0) > 0)
    .sort((a, b) => (b.put_oi ?? 0) - (a.put_oi ?? 0));

  const topCallWall = callsByOI[0]?.strike_price ?? null;
  const topPutWall  = putsByOI[0]?.strike_price ?? null;

  // Directional bias from OI structure
  let bias: string;
  let biasColor: string;
  let biasReason: string;

  if (topCallWall != null && topPutWall != null) {
    const callWallDist = topCallWall - spotPrice;
    const putWallDist  = spotPrice - topPutWall;

    if (pcr > 1.2 && putWallDist > callWallDist * 0.6) {
      bias = 'BULL'; biasColor = 'text-bull';
      biasReason = `Put wall ${topPutWall} supports upside, PCR ${pcr.toFixed(2)}`;
    } else if (pcr < 0.7 && callWallDist > putWallDist * 0.6) {
      bias = 'BEAR'; biasColor = 'text-bear';
      biasReason = `Call wall ${topCallWall} caps upside, PCR ${pcr.toFixed(2)}`;
    } else if (callWallDist < spotPrice * 0.01 && putWallDist < spotPrice * 0.01) {
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

  // Unusual OI concentration (strike OI > 2.5× average)
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

  // Manipulation detection
  let manipulation = false;
  let manipReason: string | null = null;

  // Check 1: Synthetic pinning — heavy writing on BOTH sides near ATM
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
    manipulation = true;
    manipReason = `Equal CE+PE walls at ATM (${nearRatio.toFixed(0)}% balanced, ${((nearCallOI + nearPutOI) / (totalCallOI + totalPutOI) * 100).toFixed(0)}% of total OI) — likely pinning`;
  }

  // Check 2: Volume divergence from OI direction
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

  // Max pain estimate
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
