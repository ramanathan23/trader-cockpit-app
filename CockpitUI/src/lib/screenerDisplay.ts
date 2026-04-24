/** Display helpers for screener table and card views — eliminates duplication. */

export function screenerPctColor(value?: number | null, invert = false): string {
  if (value == null) return 'rgb(var(--ghost))';
  const score = invert ? -value : value;
  if (score >= 2)  return 'rgb(var(--bull))';
  if (score >= 0)  return 'rgb(var(--fg))';
  if (score >= -3) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

export function screenerPctText(value?: number | null, forcePlus = false): string {
  if (value == null) return '-';
  const prefix = value > 0 || (forcePlus && value >= 0) ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

export function screenerF52hColor(f52h?: number | null): string {
  if (f52h == null) return 'rgb(var(--ghost))';
  if (f52h >= -2)  return 'rgb(var(--bull))';
  if (f52h >= -10) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

export function screenerF52lColor(f52l?: number | null): string {
  if (f52l == null) return 'rgb(var(--ghost))';
  if (f52l > 50)   return 'rgb(var(--bull))';
  if (f52l > 20)   return 'rgb(var(--amber))';
  if (f52l > 5)    return 'rgb(var(--fg))';
  return 'rgb(var(--bear))';
}

export function screenerStageColor(stage?: string): string {
  switch (stage) {
    case 'STAGE_2': return 'rgb(var(--bull))';
    case 'STAGE_4': return 'rgb(var(--bear))';
    case 'STAGE_1': return 'rgb(var(--amber))';
    default:        return 'rgb(var(--ghost))';
  }
}

export function screenerStageLabel(stage?: string): string {
  if (!stage) return '-';
  return stage.replace('STAGE_', 'S');
}
