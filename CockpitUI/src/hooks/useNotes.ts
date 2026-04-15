'use client';

import { useCallback, useState } from 'react';

export function useNotes() {
  const [notes, setNotes] = useState<Record<string, string>>(() => {
    if (typeof window === 'undefined') return {};
    const result: Record<string, string> = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith('cockpit:note:')) {
        const v = localStorage.getItem(k);
        if (v) result[k.slice('cockpit:note:'.length)] = v;
      }
    }
    return result;
  });

  const saveNote = useCallback((id: string, text: string) => {
    const trimmed = text.trim();
    setNotes(prev => {
      const next = { ...prev };
      if (trimmed) {
        next[id] = trimmed;
        localStorage.setItem(`cockpit:note:${id}`, trimmed);
      } else {
        delete next[id];
        localStorage.removeItem(`cockpit:note:${id}`);
      }
      return next;
    });
  }, []);

  return { notes, saveNote };
}
