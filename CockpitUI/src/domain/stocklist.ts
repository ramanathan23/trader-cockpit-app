import type { ScreenerRow } from './screener';

export interface StockRow extends ScreenerRow {
  company_name?: string | null;
  current_price?: number;
}

export function sortStockRows(rows: StockRow[], col: string, asc: boolean): StockRow[] {
  return [...rows].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[col];
    const bv = (b as unknown as Record<string, unknown>)[col];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const dir = asc ? 1 : -1;
    if (typeof av === 'string') return (av as string).localeCompare(bv as string) * dir;
    return ((av as number) < (bv as number) ? -1 : (av as number) > (bv as number) ? 1 : 0) * dir;
  });
}
