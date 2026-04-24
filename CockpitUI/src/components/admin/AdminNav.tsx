'use client';

import type { AdminSection, NavItem } from './adminTypes';
import { NAV } from './adminConstants';

interface AdminNavProps {
  section: AdminSection;
  onSection: (s: AdminSection) => void;
}

/** Single nav button in the admin sidebar. */
function NavButton({ item, active, onClick }: { item: NavItem; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${
        active
          ? 'border-accent/40 bg-accent/10 text-fg'
          : 'border-transparent text-dim hover:border-border hover:bg-lift/60 hover:text-fg'
      }`}
    >
      <span className="block text-[12px] font-black leading-tight">{item.label}</span>
      <span className="mt-0.5 block text-[10px] text-ghost">{item.caption}</span>
    </button>
  );
}

/** Left sidebar navigation for the admin panel. Groups nav items under headings. */
export function AdminNav({ section, onSection }: AdminNavProps) {
  const grouped = NAV.reduce<{ ungrouped: NavItem[]; grouped: Record<string, NavItem[]> }>(
    (acc, item) => {
      if (!item.group) acc.ungrouped.push(item);
      else (acc.grouped[item.group] ??= []).push(item);
      return acc;
    },
    { ungrouped: [], grouped: {} },
  );

  return (
    <aside className="w-44 shrink-0 border-r border-border bg-panel/60 p-2 overflow-y-auto">
      <nav className="flex flex-col gap-0.5">
        {grouped.ungrouped.map(item => (
          <NavButton key={item.key} item={item} active={section === item.key} onClick={() => onSection(item.key)} />
        ))}
        {Object.entries(grouped.grouped).map(([groupName, items]) => (
          <div key={groupName} className="mt-3">
            <p className="mb-1 px-2 text-[9px] font-black uppercase tracking-widest text-ghost/50">{groupName}</p>
            {items.map(item => (
              <NavButton key={item.key} item={item} active={section === item.key} onClick={() => onSection(item.key)} />
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
