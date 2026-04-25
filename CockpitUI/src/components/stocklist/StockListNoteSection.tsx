'use client';

import { memo, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { fmtDateTime } from '@/lib/fmt';
import type { NoteEntry } from '@/hooks/useNotes';

interface NoteSectionProps {
  symbol:   string;
  entries:  NoteEntry[];
  onAdd:    (symbol: string, text: string) => void;
  onDelete: (symbol: string, id: string)   => void;
}

const NoteRow = memo(({ entry, symbol, onDelete }: {
  entry: NoteEntry; symbol: string; onDelete: NoteSectionProps['onDelete'];
}) => (
  <div className="flex items-start gap-2 rounded-md border border-border/50 bg-base/60 px-3 py-2">
    <div className="min-w-0 flex-1">
      <div className="text-meta text-ghost">{entry.createdAt ? fmtDateTime(entry.createdAt) : 'Legacy'}</div>
      <div className="mt-0.5 text-[12px] leading-snug text-fg">{entry.text}</div>
    </div>
    <button type="button"
      className="icon-btn h-5 w-5 shrink-0 text-ghost hover:text-bear"
      onClick={() => onDelete(symbol, entry.id)}>
      <Trash2 size={10} />
    </button>
  </div>
));
NoteRow.displayName = 'NoteRow';

export const StockListNoteSection = memo(({ symbol, entries, onAdd, onDelete }: NoteSectionProps) => {
  const [draft, setDraft] = useState('');

  const submit = () => {
    if (!draft.trim()) return;
    onAdd(symbol, draft);
    setDraft('');
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="label-xs">Notes ({entries.length})</div>
      <div className="flex max-h-[150px] flex-col gap-1.5 overflow-y-auto">
        {entries.length === 0
          ? <div className="text-[11px] text-ghost">No notes yet.</div>
          : entries.map(e => <NoteRow key={e.id} entry={e} symbol={symbol} onDelete={onDelete} />)}
      </div>
      <div className="flex gap-2">
        <textarea
          className="field min-h-[52px] flex-1 resize-none text-[12px]"
          placeholder="Add a note…"
          rows={2}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit(); }}
        />
        <button type="button"
          className="rounded-md border border-accent/40 bg-accent/10 px-3 text-[11px] font-black text-accent hover:bg-accent/20 disabled:opacity-40"
          disabled={!draft.trim()}
          onClick={submit}>
          Add
        </button>
      </div>
      <div className="text-[10px] text-ghost">Ctrl+Enter to save</div>
    </div>
  );
});
StockListNoteSection.displayName = 'StockListNoteSection';
