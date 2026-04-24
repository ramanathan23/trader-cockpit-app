'use client';

import { memo } from 'react';

interface SignalNoteCellProps {
  id: string;
  symbol: string;
  isFno?: boolean;
  note?: string;
  onNoteClick: (id: string) => void;
  onOptionChain?: (sym: string) => void;
}

/** Last table cell — OC shortcut button, note trigger, and note preview. */
export const SignalNoteCell = memo(({ id, symbol, isFno, note, onNoteClick, onOptionChain }: SignalNoteCellProps) => (
  <td>
    <div className="flex max-w-[190px] items-center gap-2">
      {isFno && (
        <button type="button"
          onClick={e => { e.stopPropagation(); onOptionChain?.(symbol); }}
          className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
          title="View option chain">OC</button>
      )}
      <button type="button"
        onClick={e => { e.stopPropagation(); onNoteClick(id); }}
        className="text-[10px] font-bold text-ghost opacity-0 transition-opacity hover:text-fg group-hover:opacity-100"
        title={note || 'Add note'}>Note</button>
      {note && <span className="truncate text-[10px] text-dim" title={note}>{note}</span>}
    </div>
  </td>
));
SignalNoteCell.displayName = 'SignalNoteCell';
