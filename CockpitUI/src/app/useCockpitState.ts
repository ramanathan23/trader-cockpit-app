import { useEffect, useState } from 'react';
import type { SignalCategory, SignalType } from '@/domain/signal';
import type { AppView, ThemeMode } from './appTypes';

export function useCockpitState() {
  const [view,     setView]     = useState<AppView>('dashboard');
  const [category, setCategory] = useState<SignalCategory>('ALL');
  const [minAdvCr, setMinAdvCr] = useState(0);
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table');
  const [showHelp, setShowHelp] = useState(false);
  const [theme,    setTheme]    = useState<ThemeMode>('dark');
  const [subType,  setSubType]  = useState<SignalType | null>(null);
  const [fnoOnly,  setFnoOnly]  = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem('trader-cockpit-theme');
    if (stored === 'dark' || stored === 'light') { setTheme(stored); return; }
    setTheme(window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('trader-cockpit-theme', theme);
  }, [theme]);

  return {
    view,     setView,
    category, setCategory,
    minAdvCr, setMinAdvCr,
    viewMode, setViewMode,
    showHelp, setShowHelp,
    theme,    setTheme,
    subType,  setSubType,
    fnoOnly,  setFnoOnly,
  };
}
