'use client';

import { useCallback, useMemo, useState } from 'react';

export interface NoteEntry {
  id:        string;
  text:      string;
  createdAt: string;
}

function persist(symbol: string, entries: NoteEntry[]) {
  const key = `cockpit:notes:${symbol}`;
  if (entries.length === 0) localStorage.removeItem(key);
  else localStorage.setItem(key, JSON.stringify(entries));
}

function initEntries(): Record<string, NoteEntry[]> {
  if (typeof window === 'undefined') return {};
  const result: Record<string, NoteEntry[]> = {};
  const seen = new Set<string>();
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k?.startsWith('cockpit:notes:')) {
      const sym = k.slice('cockpit:notes:'.length);
      seen.add(sym);
      try { result[sym] = JSON.parse(localStorage.getItem(k)!); } catch {}
    }
  }
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k?.startsWith('cockpit:note:')) {
      const sym = k.slice('cockpit:note:'.length);
      if (!seen.has(sym)) {
        const v = localStorage.getItem(k);
        if (v?.trim()) result[sym] = [{ id: '0', text: v.trim(), createdAt: '' }];
      }
    }
  }
  return result;
}

export function useNotes() {
  const [noteEntries, setNoteEntries] = useState<Record<string, NoteEntry[]>>(initEntries);

  const addNote = useCallback((symbol: string, text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const entry: NoteEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      text: trimmed,
      createdAt: new Date().toISOString(),
    };
    setNoteEntries(prev => {
      const next = { ...prev, [symbol]: [entry, ...(prev[symbol] ?? [])] };
      persist(symbol, next[symbol]);
      return next;
    });
  }, []);

  const deleteNote = useCallback((symbol: string, id: string) => {
    setNoteEntries(prev => {
      const entries = (prev[symbol] ?? []).filter(e => e.id !== id);
      const next = { ...prev };
      if (entries.length === 0) delete next[symbol]; else next[symbol] = entries;
      persist(symbol, entries);
      return next;
    });
  }, []);

  const saveNote = useCallback((symbol: string, text: string) => {
    const trimmed = text.trim();
    setNoteEntries(prev => {
      const next = { ...prev };
      if (!trimmed) { delete next[symbol]; persist(symbol, []); }
      else {
        const entry: NoteEntry = { id: '0', text: trimmed, createdAt: new Date().toISOString() };
        next[symbol] = [entry];
        persist(symbol, [entry]);
      }
      return next;
    });
  }, []);

  const notes = useMemo(() => {
    const r: Record<string, string> = {};
    for (const [sym, entries] of Object.entries(noteEntries)) {
      if (entries.length > 0) r[sym] = entries[0].text;
    }
    return r;
  }, [noteEntries]);

  return { notes, noteEntries, addNote, deleteNote, saveNote };
}
