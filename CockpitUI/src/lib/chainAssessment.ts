import type { OptionStrike } from '@/domain/option_chain';

export interface AssessResult { label: string; color: string; reasons: string[]; }

export function assessChain(strikes: OptionStrike[], spotPrice: number): AssessResult {
  if (strikes.length === 0) return { label: 'No data', color: 'rgb(var(--ghost))', reasons: [] };

  const reasons: string[] = [];
  let score = 0;

  const ivs   = strikes.flatMap(s => [s.call_iv, s.put_iv].filter((v): v is number => v != null && v > 0));
  const avgIV = ivs.length ? ivs.reduce((a, v) => a + v, 0) / ivs.length : 0;

  if (avgIV > 0) {
    if (avgIV < 25)      { score += 1; reasons.push(`Low IV ${avgIV.toFixed(1)}%`); }
    else if (avgIV > 40) { score -= 1; reasons.push(`High IV ${avgIV.toFixed(1)}%`); }
    else                 {             reasons.push(`Moderate IV ${avgIV.toFixed(1)}%`); }
  }

  const atm = strikes.reduce((best, s) =>
    Math.abs(s.strike_price - spotPrice) < Math.abs(best.strike_price - spotPrice) ? s : best,
    strikes[0],
  );
  const spreads = [
    atm.call_ask != null && atm.call_bid != null && atm.call_bid > 0 ? (atm.call_ask - atm.call_bid) / atm.call_bid * 100 : null,
    atm.put_ask  != null && atm.put_bid  != null && atm.put_bid  > 0 ? (atm.put_ask  - atm.put_bid)  / atm.put_bid  * 100 : null,
  ].filter((v): v is number => v != null);

  if (spreads.length) {
    const spread = spreads.reduce((a, v) => a + v, 0) / spreads.length;
    if (spread < 1) score += 1;
    if (spread > 3) score -= 1;
    reasons.push(`Spread ${spread.toFixed(1)}%`);
  }

  const totalCallOI = strikes.reduce((a, r) => a + (r.call_oi     ?? 0), 0);
  const totalPutOI  = strikes.reduce((a, r) => a + (r.put_oi      ?? 0), 0);
  const totalVol    = strikes.reduce((a, r) => a + (r.call_volume  ?? 0) + (r.put_volume ?? 0), 0);

  if (totalCallOI + totalPutOI > 0) {
    const pcr = totalPutOI / (totalCallOI || 1);
    reasons.push(`PCR ${pcr.toFixed(2)}`);
    if (pcr > 1.2) score += 1;
    if (pcr < 0.7) score -= 1;
  }

  if (totalVol === 0)       { score -= 2; reasons.push('No traded volume'); }
  else if (totalVol < 1000) {             reasons.push('Low volume'); }

  return {
    label: score >= 2 ? 'Favourable for buying' : score >= 0 ? 'Neutral' : 'Unfavourable for buying',
    color: score >= 2 ? 'rgb(var(--bull))' : score >= 0 ? 'rgb(var(--amber))' : 'rgb(var(--bear))',
    reasons,
  };
}

export function fmtOI(v: number | null | undefined): string {
  if (v == null) return '-';
  if (v >= 100_000) return `${(v / 100_000).toFixed(1)}L`;
  if (v >= 1_000)   return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

export const fmtIV    = (v: number | null | undefined): string => v != null ? `${v.toFixed(1)}%` : '-';
export const fmtGreek = (v: number | null | undefined): string => v != null ? v.toFixed(2) : '-';
