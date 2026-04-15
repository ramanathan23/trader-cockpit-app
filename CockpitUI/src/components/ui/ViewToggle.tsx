'use client';

interface ViewToggleProps {
  view: 'card' | 'table';
  onChange: (v: 'card' | 'table') => void;
}

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="flex rounded-[5px] overflow-hidden border border-border bg-panel">
      <button
        onClick={() => onChange('card')}
        title="Card view"
        className={`p-1.5 transition-all ${
          view === 'card' ? 'bg-lift text-fg' : 'bg-transparent text-ghost hover:text-dim'
        }`}
      >
        <svg width="13" height="13" viewBox="0 0 13 13" fill="currentColor">
          <rect x="0" y="0" width="5.5" height="5.5" rx="1"/>
          <rect x="7.5" y="0" width="5.5" height="5.5" rx="1"/>
          <rect x="0" y="7.5" width="5.5" height="5.5" rx="1"/>
          <rect x="7.5" y="7.5" width="5.5" height="5.5" rx="1"/>
        </svg>
      </button>
      <button
        onClick={() => onChange('table')}
        title="Table view"
        className={`p-1.5 border-l border-border transition-all ${
          view === 'table' ? 'bg-lift text-fg' : 'bg-transparent text-ghost hover:text-dim'
        }`}
      >
        <svg width="13" height="13" viewBox="0 0 14 14" fill="currentColor">
          <rect x="0" y="1"  width="14" height="2.2" rx="1"/>
          <rect x="0" y="6"  width="14" height="2.2" rx="1"/>
          <rect x="0" y="11" width="14" height="2.2" rx="1"/>
        </svg>
      </button>
    </div>
  );
}
