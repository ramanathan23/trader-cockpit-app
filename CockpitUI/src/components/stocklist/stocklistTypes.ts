export interface ColDef {
  key:    string;
  label:  string;
  title?: string;
  align?: 'left' | 'right';
}

export const STOCK_COLS: ColDef[] = [
  { key: 'symbol',        label: 'Symbol', align: 'left'  },
  { key: 'stage',         label: 'Stage',  align: 'left'  },
  { key: 'display_price', label: 'Price',  align: 'right' },
  { key: 'chg_pct',       label: 'Chg%',   align: 'right' },
  { key: 'atr_14',        label: 'ATR',    title: 'ATR(14) in ₹', align: 'right' },
  { key: 'adv_20_cr',     label: 'ADV',    title: '20-day avg daily volume (Cr)', align: 'right' },
  { key: 'f52h',          label: '52H%',   title: '% from 52-week high', align: 'right' },
  { key: '_actions',      label: '',       align: 'right' },
];

export const COL_COUNT  = STOCK_COLS.length;
export const COL_SPAN   = COL_COUNT + 1;
