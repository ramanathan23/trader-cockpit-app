'use client';

import { stageColor, stageLabel } from '@/lib/stageUtils';

/** Compact stage label (S1/S2/S3/S4) colored by Weinstein stage. */
export function StageBadge({ stage }: { stage: string | null | undefined }) {
  return (
    <span className="num font-black" style={{ color: stageColor(stage) }}>
      {stageLabel(stage)}
    </span>
  );
}
