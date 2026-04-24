'use client';

import { memo, useState } from 'react';

interface NoteModalProps {
  id: string;
  note?: string;
  onSave: (id: string, text: string) => void;
  onClose: () => void;
}

export const NoteModal = memo(({ id, note, onSave, onClose }: NoteModalProps) => {
  const [draft, setDraft] = useState(note ?? '');
  const commit = () => { onSave(id, draft); onClose(); };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="surface-card w-80 p-4" onClick={e => e.stopPropagation()}>
        <p className="mb-2 text-[10px] font-black uppercase text-ghost">Note</p>
        <textarea
          autoFocus rows={4} value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); }
            if (e.key === 'Escape') onClose();
          }}
          placeholder="Add a trading note"
          className="field min-h-[84px] w-full resize-none py-2 text-[12px]"
          style={{ colorScheme: 'inherit' }}
        />
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="seg-btn">Cancel</button>
          <button type="button" onClick={commit} className="seg-btn active text-accent">Save</button>
        </div>
      </div>
    </div>
  );
});
NoteModal.displayName = 'NoteModal';
