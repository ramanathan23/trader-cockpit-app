'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';
import { STOCK_COLS } from './stocklistTypes';

interface StockListTableHeadProps {
  sortCol: string;
  sortAsc: boolean;
  onSort:  (col: string) => void;
}

export const StockListTableHead = memo(({ sortCol, sortAsc, onSort }: StockListTableHeadProps) => (
  <thead className="sticky top-0 z-10 bg-panel text-[10px] font-black uppercase tracking-wide text-ghost">
    <tr>
      <th className="w-7 px-1 py-2" />
      {STOCK_COLS.map(col => (
        <th
          key={col.key}
          title={col.title}
          className={cn(
            'whitespace-nowrap px-2 py-2',
            col.align === 'right' ? 'text-right' : 'text-left',
            col.key !== '_actions' && 'cursor-pointer hover:text-fg',
          )}
          onClick={() => col.key !== '_actions' && onSort(col.key)}
        >
          {col.label}
          {sortCol === col.key && (
            <span className="ml-0.5 text-accent">{sortAsc ? '↑' : '↓'}</span>
          )}
        </th>
      ))}
    </tr>
  </thead>
));
StockListTableHead.displayName = 'StockListTableHead';
