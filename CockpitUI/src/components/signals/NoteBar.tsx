'use client';

import { memo, useState } from 'react';

interface NoteBarProps {
  id: string;
  note?: string;
  onSave: (id: string, text: string) => void;
}

export const NoteBar = memo(({ id, note, onSave }: NoteBarProps) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const startEdit = () => { setDraft(note ?? ''); setEditing(true); };
  const commit = () => { onSave(id, draft); setEditing(false); };

  if (editing) {
    return (
      <div className="border-t border-border px-3 py-2" onClick={e => e.stopPropagation()}>
        <textarea
          autoFocus rows={2} value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); }
            if (e.key === 'Escape') setEditing(false);
          }}
          placeholder="Add a note"
          className="field min-h-[58px] w-full resize-none py-2 text-[11px]"
          style={{ colorScheme: 'inherit' }}
        />
        <div className="mt-2 flex justify-end gap-2">
          <button type="button" onClick={() => setEditing(false)} className="text-[10px] font-semibold text-ghost hover:text-fg">Cancel</button>
          <button type="button" onClick={commit} className="text-[10px] font-black text-accent">Save</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[36px] items-center gap-2 border-t border-border px-3 py-2">
      {note
        ? <span className="line-clamp-2 flex-1 text-[11px] leading-snug text-dim">{note}</span>
        : <span className="flex-1 text-[11px] text-ghost">No note</span>}
      <button type="button" onClick={e => { e.stopPropagation(); startEdit(); }}
        className="text-[10px] font-black text-ghost hover:text-fg">
        Note
      </button>
    </div>
  );
});
NoteBar.displayName = 'NoteBar';
