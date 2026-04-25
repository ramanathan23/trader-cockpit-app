import type { StockRow } from '@/domain/stocklist';

export type SetupTier = 'STRONG' | 'BUILDING' | 'WATCH';

export function setupTier(row: StockRow): SetupTier | null {
  if (!row.total_score || !row.stage) return null;
  if (row.stage === 'STAGE_4' || row.stage === 'STAGE_3') return null;

  const isStage2  = row.stage === 'STAGE_2';
  const rsiSweet  = row.rsi_14 != null && row.rsi_14 >= 44 && row.rsi_14 <= 74;
  const trendOn   = row.adx_14 != null && row.adx_14 >= 18;
  const hasSetup  = !!(row.vcp_detected || row.rect_breakout);
  const near52h   = row.f52h != null && row.f52h >= -15;

  if (isStage2 && row.total_score >= 65 && rsiSweet && trendOn && (hasSetup || near52h)) return 'STRONG';
  if (isStage2 && row.total_score >= 52) return 'BUILDING';
  if (row.total_score >= 44 && row.stage !== 'STAGE_4') return 'WATCH';
  return null;
}

export const TIER_LABEL: Record<SetupTier, string> = {
  STRONG:   '● STRONG',
  BUILDING: '◑ BUILDING',
  WATCH:    '○ WATCH',
};

export const TIER_TEXT_CLASS: Record<SetupTier, string> = {
  STRONG:   'text-bull',
  BUILDING: 'text-accent',
  WATCH:    'text-amber',
};

export const TIER_BORDER_CLASS: Record<SetupTier, string> = {
  STRONG:   'border-l-[3px] border-bull/70',
  BUILDING: 'border-l-[3px] border-accent/60',
  WATCH:    'border-l-[3px] border-amber/50',
};

export const TIER_BG_CLASS: Record<SetupTier, string> = {
  STRONG:   'bg-bull/[0.04]',
  BUILDING: 'bg-accent/[0.04]',
  WATCH:    'bg-amber/[0.03]',
};
