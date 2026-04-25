import type { AccountTab } from './accountTypes';

const TABS: { key: AccountTab; label: string }[] = [
  { key: 'configure', label: 'Configure' },
  { key: 'overall', label: 'Overall Dashboard' },
  { key: 'individual', label: 'Individual Dashboard' },
];

export function AccountTabs({ active, onChange }: { active: AccountTab; onChange: (tab: AccountTab) => void }) {
  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {TABS.map(tab => (
        <button key={tab.key} type="button" onClick={() => onChange(tab.key)}
          className={`rounded-lg border px-4 py-2 text-[12px] font-black ${active === tab.key ? 'border-accent/50 bg-accent/10 text-accent' : 'border-border text-dim hover:bg-lift hover:text-fg'}`}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
