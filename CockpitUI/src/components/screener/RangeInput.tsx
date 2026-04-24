'use client';

import type { ScreenerRangeFilter } from '@/domain/screener';

interface RangeInputProps {
  label: string;
  field: keyof ScreenerRangeFilter;
  min?: boolean;
  unit?: string;
  placeholder?: string;
  range: ScreenerRangeFilter;
  onRange: (r: ScreenerRangeFilter) => void;
}

/** Numeric input bound to a single field of ScreenerRangeFilter. */
export function RangeInput({ label, field, min, unit = '', placeholder = 'inf', range, onRange }: RangeInputProps) {
  const val = range[field];
  const displayVal = (val === Infinity || val === -Infinity) ? '' : String(val);

  return (
    <span className="flex items-center gap-1 text-[11px] text-ghost">
      {label}
      <input
        type="number"
        value={displayVal}
        placeholder={placeholder}
        className="field h-8 w-20 text-[11px]"
        onChange={e => {
          const raw = e.target.value;
          const parsed = raw === '' ? (min ? 0 : Infinity) : parseFloat(raw);
          onRange({ ...range, [field]: Number.isNaN(parsed) ? (min ? 0 : Infinity) : parsed });
        }}
      />
      {unit && <span>{unit}</span>}
    </span>
  );
}
