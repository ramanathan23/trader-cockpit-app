export interface ColDef {
  key:    string;
  label:  string;
  title?: string;
  align?: 'left' | 'right';
}

export const STOCK_COLS: ColDef[] = [
  { key: 'rank',           label: '#',     align: 'right' },
  { key: 'symbol',         label: 'Symbol',align: 'left'  },
  { key: 'stage',          label: 'Stage', align: 'left'  },
  { key: 'total_score',    label: 'Score', title: 'Composite score 0–100', align: 'right' },
  { key: 'iss_score',      label: 'Intraday', title: 'Session prediction and Intraday Suitability Score', align: 'left' },
  { key: 'display_price',  label: 'Price', align: 'right' },
  { key: 'week_return_pct',label: 'Wk%',  title: 'Week return %', align: 'right' },
  { key: 'rsi_14',         label: 'RSI',  title: 'RSI(14)', align: 'right' },
  { key: 'adx_14',         label: 'ADX',  title: 'ADX(14) — trend strength', align: 'right' },
  { key: 'atr_14',         label: 'ATR',  title: 'ATR(14) in ₹ — volatility range', align: 'right' },
  { key: 'adv_20_cr',      label: 'ADV',  title: '20-day avg daily volume (Cr)', align: 'right' },
  { key: 'f52h',           label: '52H%', title: '% from 52-week high (0 = at high, -10 = 10% below)', align: 'right' },
  { key: '_actions',       label: '',     align: 'right' },
];

export const COL_COUNT  = STOCK_COLS.length;
export const COL_SPAN   = COL_COUNT + 1; // +1 for the expand-chevron column
