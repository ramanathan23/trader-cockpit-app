export function money(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '-';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value);
}

export function tone(value: number) {
  return value >= 0 ? 'text-bull' : 'text-bear';
}

export function statusClass(status: string) {
  if (status === 'connected' || status === 'ok') return 'border-bull/40 bg-bull/10 text-bull';
  if (status === 'error') return 'border-bear/40 bg-bear/10 text-bear';
  return 'border-warn/40 bg-warn/10 text-warn';
}

export function when(value: string | null | undefined) {
  return value?.slice(0, 16).replace('T', ' ') ?? '-';
}

export function holdMinutes(entry: string | null, exit: string | null): number {
  if (!entry || !exit) return 0;
  return Math.max(0, Math.round((new Date(exit).getTime() - new Date(entry).getTime()) / 60000));
}

export function fmtHold(minutes: number): string {
  if (minutes <= 0) return '-';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}
