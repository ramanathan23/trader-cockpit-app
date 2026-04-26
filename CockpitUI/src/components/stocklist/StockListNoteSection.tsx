'use client';

import { memo, useState } from 'react';
import { Send, Trash2 } from 'lucide-react';
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
  <div className="group flex items-start gap-2 rounded-md border border-border/45 bg-base/45 px-3 py-2">
    <div className="min-w-0 flex-1">
      <div className="text-meta text-ghost">{entry.createdAt ? fmtDateTime(entry.createdAt) : 'Legacy'}</div>
      <div className="mt-1 whitespace-pre-wrap text-[12px] leading-snug text-fg">{entry.text}</div>
    </div>
    <button type="button"
      className="icon-btn h-6 w-6 shrink-0 opacity-70 hover:text-bear group-hover:opacity-100"
      title="Delete note"
      onClick={() => onDelete(symbol, entry.id)}>
      <Trash2 size={12} />
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
    <div className="flex h-full flex-col rounded-lg border border-border/50 bg-card/70 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="label-sm">Notes</div>
          <div className="mt-1 text-[11px] text-ghost">{entries.length} saved</div>
        </div>
      </div>

      <div className="flex max-h-[132px] min-h-[34px] flex-col gap-1.5 overflow-y-auto pr-1">
        {entries.length === 0
          ? <div className="rounded-md border border-dashed border-border/50 px-3 py-2 text-[11px] text-ghost">No notes yet.</div>
          : entries.map(e => <NoteRow key={e.id} entry={e} symbol={symbol} onDelete={onDelete} />)}
      </div>

      <div className="mt-3 flex gap-2">
        <textarea
          className="field min-h-[58px] flex-1 resize-none py-2 text-[12px] leading-snug"
          placeholder="Add a note..."
          rows={2}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit(); }}
        />
        <button type="button"
          className="icon-btn h-[58px] w-10 shrink-0 border-accent/40 bg-accent/10 text-accent hover:bg-accent/20 disabled:opacity-40"
          title="Save note"
          disabled={!draft.trim()}
          onClick={submit}>
          <Send size={14} />
        </button>
      </div>
      <div className="mt-1.5 text-[10px] text-ghost">Ctrl+Enter to save</div>
    </div>
  );
});
StockListNoteSection.displayName = 'StockListNoteSection';
