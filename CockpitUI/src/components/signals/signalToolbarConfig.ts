import { type SignalCategory, type SignalType } from '@/domain/signal';

export const TAB_SIGNAL_TYPE: Record<SignalCategory, SignalType> = {
  ALL:    'OPEN_DRIVE_ENTRY',
  DRIVE:  'OPEN_DRIVE_ENTRY',
  SPIKE:  'SPIKE_BREAKOUT',
  ABS:    'ABSORPTION',
  EXHAUST:'EXHAUSTION_REVERSAL',
  FADE:   'FADE_ALERT',
  BREAK:  'RANGE_BREAKOUT',
  VWAP:   'VWAP_BREAKOUT',
  CAM:    'CAM_H4_BREAKOUT',
  GAP:    'GAP_UP',
};

export const TABS: { key: SignalCategory; label: string; title: string }[] = [
  { key: 'ALL',    label: 'All',      title: 'All signal categories' },
  { key: 'DRIVE',  label: 'Drive',    title: 'Open drive entries and failures' },
  { key: 'SPIKE',  label: 'Spike',    title: 'Volume spike breakouts' },
  { key: 'ABS',    label: 'Abs',      title: 'Absorption setups' },
  { key: 'EXHAUST',label: 'Exhaust',  title: 'Exhaustion reversals' },
  { key: 'FADE',   label: 'Fade',     title: 'Counter-trend fade alerts' },
  { key: 'BREAK',  label: 'Breakout', title: 'ORB, PDH/PDL, range and 52-week breakouts' },
  { key: 'VWAP',   label: 'VWAP',     title: 'VWAP reclaim and breakdown signals' },
  { key: 'CAM',    label: 'CAM',      title: 'Camarilla pivot breakouts and reversals' },
  { key: 'GAP',    label: 'Gap',      title: 'Gap-up and gap-down at session open' },
];

export const SUBTYPES_BY_CATEGORY: Partial<Record<SignalCategory, { type: SignalType; label: string; title: string }[]>> = {
  CAM: [
    { type: 'CAM_H4_BREAKOUT', label: 'H4+',    title: 'Camarilla H4 breakout' },
    { type: 'CAM_L4_BREAKDOWN',label: 'L4-',    title: 'Camarilla L4 breakdown' },
    { type: 'CAM_H3_REVERSAL', label: 'H3 rev', title: 'Camarilla H3 rejection' },
    { type: 'CAM_L3_REVERSAL', label: 'L3 rev', title: 'Camarilla L3 rejection' },
  ],
  BREAK: [
    { type: 'ORB_BREAKOUT',   label: 'ORB+',  title: 'Opening range breakout' },
    { type: 'ORB_BREAKDOWN',  label: 'ORB-',  title: 'Opening range breakdown' },
    { type: 'PDH_BREAKOUT',   label: 'PDH+',  title: 'Previous day high breakout' },
    { type: 'PDL_BREAKDOWN',  label: 'PDL-',  title: 'Previous day low breakdown' },
    { type: 'RANGE_BREAKOUT', label: 'RNG+',  title: 'Range breakout' },
    { type: 'RANGE_BREAKDOWN',label: 'RNG-',  title: 'Range breakdown' },
    { type: 'WEEK52_BREAKOUT',label: '52W+',  title: '52-week high breakout' },
    { type: 'WEEK52_BREAKDOWN',label:'52W-',  title: '52-week low breakdown' },
  ],
};

export const VALUE_TIERS = [
  { label: 'All',    cr: 0,   title: 'No liquidity filter' },
  { label: '5Cr+',  cr: 5,   title: 'Minimum Rs 5 Cr average daily traded value' },
  { label: '25Cr+', cr: 25,  title: 'Minimum Rs 25 Cr average daily traded value' },
  { label: '100Cr+',cr: 100, title: 'Minimum Rs 100 Cr average daily traded value' },
  { label: '500Cr+',cr: 500, title: 'Minimum Rs 500 Cr average daily traded value' },
];
