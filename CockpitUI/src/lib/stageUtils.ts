/** Stage display helpers — shared across Dashboard and Watchlist components. */

export function stageColor(stage: string | null | undefined): string {
  switch (stage) {
    case 'STAGE_2': return 'rgb(var(--bull))';
    case 'STAGE_4': return 'rgb(var(--bear))';
    case 'STAGE_1': return 'rgb(var(--amber))';
    case 'STAGE_3': return 'rgb(var(--violet))';
    default:        return 'rgb(var(--ghost))';
  }
}

export function stageLabel(stage: string | null | undefined): string {
  switch (stage) {
    case 'STAGE_2': return 'S2';
    case 'STAGE_4': return 'S4';
    case 'STAGE_1': return 'S1';
    case 'STAGE_3': return 'S3';
    default:        return '?';
  }
}
