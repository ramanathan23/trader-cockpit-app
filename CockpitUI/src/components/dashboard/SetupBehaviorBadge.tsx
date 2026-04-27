'use client';

import { cn } from '@/lib/cn';

const GRADE_TONE: Record<string, string> = {
  A: 'bg-bull text-white',
  B: 'bg-emerald-600 text-white',
  C: 'bg-amber text-black',
  D: 'bg-orange-500 text-white',
  AVOID: 'bg-bear text-white',
  LIQUIDITY_RISK: 'bg-violet text-white',
  NA: 'bg-dim text-ghost',
};

function scoreTone(score?: number | null) {
  if (score == null) return 'text-ghost';
  if (score >= 70) return 'text-bull';
  if (score >= 52) return 'text-amber';
  return 'text-bear';
}

export function SetupBehaviorBadge({
  executionScore,
  executionGrade,
  fakeoutRate,
  liquidityScore,
  compact = false,
}: {
  executionScore?: number | null;
  executionGrade?: string | null;
  fakeoutRate?: number | null;
  liquidityScore?: number | null;
  compact?: boolean;
}) {
  if (executionScore == null && !executionGrade && fakeoutRate == null && liquidityScore == null) return null;
  const grade = executionGrade ?? 'NA';

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1">
      <span
        className={cn(
          'rounded px-1.5 py-0.5 text-[10px] font-black leading-none',
          GRADE_TONE[grade] ?? GRADE_TONE.NA,
        )}
        title="Historical setup obedience grade"
      >
        {compact && grade === 'LIQUIDITY_RISK' ? 'LIQ' : grade}
      </span>
      {executionScore != null && (
        <span className={cn('num text-[10px] font-black', scoreTone(executionScore))} title="Execution quality score">
          EX {executionScore.toFixed(0)}
        </span>
      )}
      {fakeoutRate != null && !compact && (
        <span className="num text-[10px] text-ghost" title="Historical fakeout rate">
          FK {(fakeoutRate * 100).toFixed(0)}%
        </span>
      )}
      {liquidityScore != null && liquidityScore < 45 && (
        <span className="num text-[10px] text-violet" title="Liquidity score">
          LQ {liquidityScore.toFixed(0)}
        </span>
      )}
    </div>
  );
}
