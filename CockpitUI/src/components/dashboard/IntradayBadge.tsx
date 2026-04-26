'use client';

import { cn } from '@/lib/cn';
import type { IntradaySessionType } from '@/domain/dashboard';

const SESSION_COLOR: Record<IntradaySessionType, string> = {
  TREND_UP: 'bg-bull',
  TREND_DOWN: 'bg-bear',
  CHOP: 'bg-amber',
  VOLATILE: 'bg-orange-500',
  GAP_FADE: 'bg-violet',
  NEUTRAL: 'bg-dim',
};

export function IntradayBadge({
  sessionType,
  issScore,
  pullbackPred,
  compact = false,
}: {
  sessionType?: IntradaySessionType | null;
  issScore?: number | null;
  pullbackPred?: number | null;
  compact?: boolean;
}) {
  if (!sessionType && issScore == null && pullbackPred == null) return null;
  const issTone = issScore == null
    ? 'text-ghost'
    : issScore >= 60
      ? 'text-bull'
      : issScore >= 40
        ? 'text-amber'
        : 'text-bear';

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1">
      {sessionType && (
        <span
          className={cn(
            'rounded px-1.5 py-0.5 text-[10px] font-black leading-none text-white',
            SESSION_COLOR[sessionType],
          )}
          title="Predicted intraday session type"
        >
          {compact ? sessionType.replace('TREND_', 'T_') : sessionType}
        </span>
      )}
      {issScore != null && (
        <span className={cn('num text-[10px] font-black', issTone)} title="Intraday Suitability Score">
          ISS {issScore.toFixed(0)}
        </span>
      )}
      {pullbackPred != null && (
        <span className="num text-[10px] text-ghost" title="Predicted pullback depth">
          PB {(pullbackPred * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}
