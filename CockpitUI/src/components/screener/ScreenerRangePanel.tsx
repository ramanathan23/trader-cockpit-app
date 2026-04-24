'use client';

import { memo } from 'react';
import { DEFAULT_RANGE, type ScreenerRangeFilter } from '@/domain/screener';
import { RangeInput } from './RangeInput';

interface ScreenerRangePanelProps {
  range: ScreenerRangeFilter;
  onRange: (r: ScreenerRangeFilter) => void;
}

/** Expanded panel with numeric range inputs for ATR, Close, ADV, 52H%, and 52L%. */
export const ScreenerRangePanel = memo(({ range, onRange }: ScreenerRangePanelProps) => (
  <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-border bg-base/35 px-4 py-3">
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-black uppercase text-ghost">ATR</span>
      <RangeInput label="min" field="atrMin" min range={range} onRange={onRange} placeholder="0" />
      <RangeInput label="max" field="atrMax" range={range} onRange={onRange} />
    </div>
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-black uppercase text-ghost">Close</span>
      <RangeInput label="min" field="closeMin" min range={range} onRange={onRange} placeholder="0" />
      <RangeInput label="max" field="closeMax" range={range} onRange={onRange} />
    </div>
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-black uppercase text-ghost">ADV</span>
      <RangeInput label="min" field="advMin" min range={range} onRange={onRange} placeholder="0" />
      <RangeInput label="max" field="advMax" range={range} onRange={onRange} unit="Cr" />
    </div>
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-black uppercase text-ghost">52H%</span>
      <RangeInput label="from" field="f52hMin" range={range} onRange={onRange} placeholder="-inf" />
      <RangeInput label="to"   field="f52hMax" range={range} onRange={onRange} placeholder="0" />
    </div>
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-black uppercase text-ghost">52L%</span>
      <RangeInput label="from" field="f52lMin" min range={range} onRange={onRange} placeholder="0" />
      <RangeInput label="to"   field="f52lMax" range={range} onRange={onRange} />
    </div>
    <button type="button" onClick={() => onRange(DEFAULT_RANGE)}
      className="text-[11px] font-bold text-ghost hover:text-fg">Reset ranges</button>
  </div>
));
ScreenerRangePanel.displayName = 'ScreenerRangePanel';
