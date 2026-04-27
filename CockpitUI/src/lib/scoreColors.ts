/** Color helpers for scored symbol indicators — shared across Dashboard components. */

export function rsiColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 70)  return 'rgb(var(--bear))';
  if (v <= 30)  return 'rgb(var(--bull))';
  return 'rgb(var(--amber))';
}
