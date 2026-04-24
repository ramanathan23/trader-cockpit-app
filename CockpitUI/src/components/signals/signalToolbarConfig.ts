import { type SignalCategory, type SignalType } from '@/domain/signal';

export const TAB_SIGNAL_TYPE: Record<SignalCategory, SignalType> = {
  ALL:   'RANGE_BREAKOUT',
  BREAK: 'RANGE_BREAKOUT',
  CAM:   'CAM_H4_BREAKOUT',
};

export const TABS: { key: SignalCategory; label: string; title: string }[] = [
  { key: 'ALL',   label: 'All',     title: 'All signal categories' },
  { key: 'BREAK', label: 'Breakout', title: 'Rectangle consolidation breakouts' },
  { key: 'CAM',   label: 'CAM',     title: 'Camarilla pivot breakouts and reversals' },
];

export const SUBTYPES_BY_CATEGORY: Partial<Record<SignalCategory, { type: SignalType; label: string; title: string }[]>> = {
  BREAK: [
    { type: 'RANGE_BREAKOUT',  label: 'RNG+', title: 'Rectangle breakout' },
    { type: 'RANGE_BREAKDOWN', label: 'RNG-', title: 'Rectangle breakdown' },
  ],
  CAM: [
    { type: 'CAM_H4_BREAKOUT',  label: 'H4+',  title: 'H4 breakout — narrow pivot range' },
    { type: 'CAM_L4_BREAKDOWN', label: 'L4-',  title: 'L4 breakdown — narrow pivot range' },
    { type: 'CAM_H4_REVERSAL',  label: 'H4↓',  title: 'Bearish pin at H4 — wide pivot range' },
    { type: 'CAM_H3_REVERSAL',  label: 'H3↓',  title: 'Bearish pin at H3 — wide pivot range' },
    { type: 'CAM_L3_REVERSAL',  label: 'L3↑',  title: 'Bullish pin at L3 — wide pivot range' },
    { type: 'CAM_L4_REVERSAL',  label: 'L4↑',  title: 'Bullish pin at L4 — wide pivot range' },
  ],
};

export const VALUE_TIERS = [
  { label: 'All',    cr: 0,   title: 'No liquidity filter' },
  { label: '5Cr+',  cr: 5,   title: 'Minimum Rs 5 Cr average daily traded value' },
  { label: '25Cr+', cr: 25,  title: 'Minimum Rs 25 Cr average daily traded value' },
  { label: '100Cr+',cr: 100, title: 'Minimum Rs 100 Cr average daily traded value' },
  { label: '500Cr+',cr: 500, title: 'Minimum Rs 500 Cr average daily traded value' },
];
