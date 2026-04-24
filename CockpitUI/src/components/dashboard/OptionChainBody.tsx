'use client';

import { memo } from 'react';
import type { OptionChainResponse, OptionStrike } from '@/domain/option_chain';
import type { AssessResult } from '@/lib/chainAssessment';
import { fmtOI, fmtIV, fmtGreek } from '@/lib/chainAssessment';
import { fmt2 } from '@/lib/fmt';
import { cn } from '@/lib/cn';

interface OptionChainBodyProps {
  chain:          OptionChainResponse | null;
  visibleStrikes: OptionStrike[];
  atmStrike:      number | null;
  loading:        boolean;
  error:          string | null;
  assessment:     AssessResult | null;
}

const CALL_HDRS = ['OI', 'Vol', 'IV', 'Delta', 'Bid', 'Ask', 'LTP'] as const;
const PUT_HDRS  = ['LTP', 'Bid', 'Ask', 'Delta', 'IV', 'Vol', 'OI'] as const;

export const OptionChainBody = memo(({ chain, visibleStrikes, atmStrike, loading, error, assessment }: OptionChainBodyProps) => (
  <>
    {assessment && !loading && (
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-base/35 px-4 py-2 text-[11px]">
        <span className="font-black" style={{ color: assessment.color }}>{assessment.label}</span>
        {assessment.reasons.map(r => <span key={r} className="text-ghost">{r}</span>)}
      </div>
    )}
    {loading && <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading option chain</div>}
    {error && !loading && <div className="flex flex-1 items-center justify-center text-[13px] text-bear">Error: {error}</div>}
    {chain && !loading && !error && (
      <div className="table-wrap flex-1">
        <table className="data-table text-[11px]">
          <thead>
            <tr>
              <th colSpan={7} className="text-right text-bull">Calls</th>
              <th className="text-center text-accent">Strike</th>
              <th colSpan={7} className="text-left text-bear">Puts</th>
            </tr>
            <tr>
              {CALL_HDRS.map(h => <th key={`c-${h}`} className="text-right">{h}</th>)}
              <th className="text-center">Strike</th>
              {PUT_HDRS.map(h => <th key={`p-${h}`} className="text-left">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {visibleStrikes.map(s => {
              const isATM   = atmStrike != null && s.strike_price === atmStrike;
              const itmCall = chain.spot_price > s.strike_price;
              const itmPut  = chain.spot_price < s.strike_price;
              return (
                <tr key={s.strike_price} className={cn(isATM && 'bg-accent/10')}>
                  <td className="num text-right text-dim">{fmtOI(s.call_oi)}</td>
                  <td className="num text-right text-dim">{fmtOI(s.call_volume)}</td>
                  <td className="num text-right text-amber">{fmtIV(s.call_iv)}</td>
                  <td className="num text-right text-dim">{fmtGreek(s.call_delta)}</td>
                  <td className="num text-right text-dim">{fmt2(s.call_bid)}</td>
                  <td className="num text-right text-dim">{fmt2(s.call_ask)}</td>
                  <td className={cn('num text-right font-black', itmCall ? 'text-bull' : 'text-fg')}>{fmt2(s.call_ltp)}</td>
                  <td className={cn('num text-center font-black', isATM ? 'text-accent' : 'text-fg')}>{s.strike_price}{isATM ? ' ATM' : ''}</td>
                  <td className={cn('num text-left font-black', itmPut  ? 'text-bear' : 'text-fg')}>{fmt2(s.put_ltp)}</td>
                  <td className="num text-left text-dim">{fmt2(s.put_bid)}</td>
                  <td className="num text-left text-dim">{fmt2(s.put_ask)}</td>
                  <td className="num text-left text-dim">{fmtGreek(s.put_delta)}</td>
                  <td className="num text-left text-amber">{fmtIV(s.put_iv)}</td>
                  <td className="num text-left text-dim">{fmtOI(s.put_volume)}</td>
                  <td className="num text-left text-dim">{fmtOI(s.put_oi)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    )}
  </>
));
OptionChainBody.displayName = 'OptionChainBody';
