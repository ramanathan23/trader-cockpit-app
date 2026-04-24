'use client';

import { memo } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';

const COLS: { key: string; label: string; title?: string; align?: 'left' | 'right' }[] = [
  { key: 'symbol',          label: 'Symbol',  align: 'left' },
  { key: 'stage',           label: 'Stage',   title: 'Weinstein stage' },
  { key: 'adv_20_cr',       label: 'ADV' },
  { key: 'atr_14',          label: 'ATR' },
  { key: 'display_price',   label: 'Price',   title: 'Live price when available, otherwise previous close' },
  { key: 'dvwap_delta_pct', label: 'DVWAP%',  title: 'Percent above or below session VWAP' },
  { key: 'ema50_delta_pct', label: '50E%',    title: 'Percent above or below 50-day EMA' },
  { key: 'ema200_delta_pct',label: '200E%',   title: 'Percent above or below 200-day EMA' },
  { key: 'rs_vs_nifty',     label: 'RS',      title: 'Relative strength vs Nifty 500' },
  { key: 'f52h',            label: '52H%',    title: 'Distance from 52-week high' },
  { key: 'f52l',            label: '52L%',    title: 'Distance from 52-week low' },
  { key: 'week_return_pct', label: 'WK%',     title: 'Five-session return' },
  { key: 'week_gain_pct',   label: 'W+%',     title: 'Percent above rolling five-session low' },
  { key: 'week_decline_pct',label: 'W-%',     title: 'Percent below rolling five-session high' },
];

export { COLS };

interface ScreenerTableHeadProps {
  sortCol: string;
  sortAsc: boolean;
  onSort: (col: string) => void;
}

export const ScreenerTableHead = memo(({ sortCol, sortAsc, onSort }: ScreenerTableHeadProps) => (
  <thead>
    <tr>
      <th colSpan={5} className="border-r border-border/50 text-left">Price data</th>
      <th colSpan={4} className="border-r border-border/50 text-left">Indicators</th>
      <th colSpan={5} className="text-left">52-week and momentum</th>
    </tr>
    <tr>
      {COLS.map(col => (
        <th key={col.key} title={col.title} onClick={() => onSort(col.key)}
          className={cn(col.align === 'left' ? 'text-left' : 'text-right', 'cursor-pointer hover:text-fg', sortCol === col.key && 'text-accent')}>
          <span className="inline-flex items-center gap-0.5">
            {col.label}
            <span className="inline-flex opacity-60">
              {sortCol === col.key
                ? sortAsc ? <ChevronUp size={11} /> : <ChevronDown size={11} />
                : <ChevronsUpDown size={11} className="opacity-50" />}
            </span>
          </span>
        </th>
      ))}
    </tr>
  </thead>
));
ScreenerTableHead.displayName = 'ScreenerTableHead';
