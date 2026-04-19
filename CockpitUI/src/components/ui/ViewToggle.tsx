'use client';

interface ViewToggleProps {
  view: 'card' | 'table';
  onChange: (v: 'card' | 'table') => void;
}

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="seg-group">
      <button
        type="button"
        onClick={() => onChange('card')}
        title="Card view"
        aria-label="Card view"
        className={`seg-btn px-2 ${view === 'card' ? 'active' : ''}`}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
          <rect x="1" y="1" width="5" height="5" rx="1" />
          <rect x="8" y="1" width="5" height="5" rx="1" />
          <rect x="1" y="8" width="5" height="5" rx="1" />
          <rect x="8" y="8" width="5" height="5" rx="1" />
        </svg>
      </button>
      <button
        type="button"
        onClick={() => onChange('table')}
        title="Table view"
        aria-label="Table view"
        className={`seg-btn px-2 ${view === 'table' ? 'active' : ''}`}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
          <rect x="1" y="2" width="12" height="2" rx="1" />
          <rect x="1" y="6" width="12" height="2" rx="1" />
          <rect x="1" y="10" width="12" height="2" rx="1" />
        </svg>
      </button>
    </div>
  );
}
