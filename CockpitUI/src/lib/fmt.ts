// Formatting utilities. Pure functions, no side effects.

export function fmt2(v?: number | null): string {
  return v != null ? v.toFixed(2) : '-';
}

export function fmtAdv(cr?: number | null): string {
  if (cr == null) return '-';
  return cr >= 100 ? `${Math.round(cr)}Cr` : `${cr.toFixed(1)}Cr`;
}

export function spct(value?: number | null, reference?: number | null): string {
  if (value == null || !reference) return '';
  const p = (value - reference) / reference * 100;
  return (p >= 0 ? '+' : '') + p.toFixed(1) + '%';
}

export function timeStr(iso?: string): string {
  if (!iso) return '';
  const aware = /Z$|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(aware);
  if (Number.isNaN(d.getTime())) return '??:??';
  return d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
}

export function todayIST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
}
