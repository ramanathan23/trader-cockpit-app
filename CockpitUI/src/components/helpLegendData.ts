export const SIGNAL_ROWS = [
  { key: 'RANGE_BREAKOUT',   label: 'RNG+',    desc: 'Rectangle consolidation broke upward on volume.' },
  { key: 'RANGE_BREAKDOWN',  label: 'RNG-',    desc: 'Rectangle consolidation broke downward on volume.' },
  { key: 'CAM_H4_BREAKOUT',  label: 'CAM H4+', desc: 'Closed above H4 on volume — narrow pivot range.' },
  { key: 'CAM_L4_BREAKDOWN', label: 'CAM L4-', desc: 'Closed below L4 on volume — narrow pivot range.' },
  { key: 'CAM_H4_REVERSAL',  label: 'CAM H4↓', desc: 'Bearish pin rejection at H4 — wide pivot range.' },
  { key: 'CAM_H3_REVERSAL',  label: 'CAM H3↓', desc: 'Bearish pin rejection at H3 — wide pivot range.' },
  { key: 'CAM_L3_REVERSAL',  label: 'CAM L3↑', desc: 'Bullish pin bounce from L3 — wide pivot range.' },
  { key: 'CAM_L4_REVERSAL',  label: 'CAM L4↑', desc: 'Bullish pin bounce from L4 — wide pivot range.' },
] as const;

export const METRIC_ROWS = [
  { key: '52H', desc: 'Distance from the 52-week high.' },
  { key: '52L', desc: 'Distance from the 52-week low.' },
  { key: 'ATR', desc: '14-day average true range for stop sizing.' },
  { key: 'ADV', desc: '20-day average daily traded value in crores.' },
  { key: 'VOL', desc: 'Volume ratio versus normal activity.' },
  { key: 'MTF', desc: '15m and 1h directional alignment.' },
  { key: 'ISS', desc: 'Intraday Suitability Score 0-100. ≥60 favourable, <40 avoid.' },
  { key: 'PB',  desc: 'Predicted pullback depth from session high. TREND_UP only.' },
];

export const PHASE_ROWS = [
  { key: 'Drive window',    time: '09:15-09:45', color: 'rgb(var(--accent))', desc: 'Fast, opening momentum.' },
  { key: 'Execution',       time: '09:45-11:30', color: 'rgb(var(--bull))',   desc: 'Cleaner signal context.' },
  { key: 'Dead zone',       time: '11:30-14:30', color: 'rgb(var(--ghost))', desc: 'Lower conviction chop.' },
  { key: 'Close momentum',  time: '14:30-15:15', color: 'rgb(var(--amber))', desc: 'Late directional flow.' },
  { key: 'Session end',     time: '15:15-15:30', color: 'rgb(var(--bear))',  desc: 'Avoid fresh unplanned risk.' },
];

export const SESSION_ROWS = [
  { key: 'TREND_UP',   color: 'rgb(var(--bull))',   desc: 'Directional up — breakout / momentum session.' },
  { key: 'TREND_DOWN', color: 'rgb(var(--bear))',   desc: 'Directional down — sells follow through.' },
  { key: 'CHOP',       color: 'rgb(var(--amber))',  desc: 'Sideways low-conviction range. Reduce size.' },
  { key: 'VOLATILE',   color: 'rgb(var(--amber))',  desc: 'High ATR, non-directional swings.' },
  { key: 'GAP_FADE',   color: 'rgb(var(--violet))', desc: 'Morning gap fading toward prior close.' },
  { key: 'NEUTRAL',    color: 'rgb(var(--ghost))',  desc: 'No dominant session character. Stand aside.' },
] as const;
