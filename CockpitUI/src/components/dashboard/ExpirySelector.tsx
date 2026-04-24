'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';

export const ExpirySelector = memo(({ expiries, selected, onSelect }: {
  expiries: string[];
  selected: string | null;
  onSelect: (exp: string) => void;
}) => (
  <div className="seg-group">
    {expiries.slice(0, 4).map(exp => (
      <button key={exp} type="button" onClick={() => onSelect(exp)}
        className={cn('seg-btn', selected === exp && 'active text-accent')}>
        {exp}
      </button>
    ))}
  </div>
));
ExpirySelector.displayName = 'ExpirySelector';
