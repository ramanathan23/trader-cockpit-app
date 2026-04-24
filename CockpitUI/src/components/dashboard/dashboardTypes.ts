/** Shared types and column definitions for the Dashboard panel. */

export type SortKey =
  | 'rank' | 'total_score' | 'momentum_score' | 'trend_score'
  | 'volatility_score' | 'structure_score' | 'adx_14' | 'rsi_14'
  | 'adv_20_cr' | 'comfort_score';

export type Segment    = 'all' | 'fno' | 'equity';
export type StageFilter = 'all' | 'stage2' | 'stage4';

export const DASHBOARD_HEADERS: {
  key: string; label: string; title: string;
  align: 'left' | 'right' | 'center'; sortable: boolean;
}[] = [
  { key: 'rank',             label: '#',       title: 'Rank',                         align: 'center', sortable: true  },
  { key: 'symbol',           label: 'Symbol',  title: 'Symbol and tags',              align: 'left',   sortable: false },
  { key: 'total_score',      label: 'Total',   title: 'Unified score',                align: 'right',  sortable: true  },
  { key: 'momentum_score',   label: 'Mom',     title: 'Momentum score',               align: 'right',  sortable: true  },
  { key: 'trend_score',      label: 'Trend',   title: 'Trend score',                  align: 'right',  sortable: true  },
  { key: 'volatility_score', label: 'Vol',     title: 'Volatility score',             align: 'right',  sortable: true  },
  { key: 'structure_score',  label: 'Struct',  title: 'Structure score',              align: 'right',  sortable: true  },
  { key: 'adx_14',           label: 'ADX',     title: 'ADX(14)',                      align: 'right',  sortable: true  },
  { key: 'rsi_14',           label: 'RSI',     title: 'RSI(14)',                      align: 'right',  sortable: true  },
  { key: 'adv_20_cr',        label: 'ADV',     title: 'Average daily value',          align: 'right',  sortable: true  },
  { key: 'stage',            label: 'Stage',   title: 'Weinstein stage',              align: 'center', sortable: false },
  { key: 'close',            label: 'Close',   title: 'Previous close',               align: 'right',  sortable: false },
  { key: 'comfort_score',    label: 'Comfort', title: 'Comfort score (hold ease)',    align: 'right',  sortable: true  },
  { key: 'oc',               label: 'OC',      title: 'Option chain',                 align: 'center', sortable: false },
];
