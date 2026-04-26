import { useEffect, useState } from 'react';
import type { SignalCategory, SignalType } from '@/domain/signal';
import type { AppView, ThemeMode } from './appTypes';

const STATE_KEY = 'trader-cockpit-ui-state';
const VIEWS = new Set<AppView>(['overview', 'stocks', 'accounts', 'live', 'history', 'admin']);
const CATEGORIES = new Set<SignalCategory>(['ALL', 'BREAK', 'CAM']);
const VIEW_MODES = new Set(['card', 'table', 'heatmap']);

export function useCockpitState() {
  const [view,     setView]     = useState<AppView>('overview');
  const [category, setCategory] = useState<SignalCategory>('ALL');
  const [minAdvCr, setMinAdvCr] = useState(0);
  const [viewMode, setViewMode] = useState<'card' | 'table' | 'heatmap'>('table');
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
    const raw = window.localStorage.getItem(STATE_KEY);
    if (!raw) return;
    try {
      const stored = JSON.parse(raw);
      if (VIEWS.has(stored.view)) setView(stored.view);
      if (CATEGORIES.has(stored.category)) setCategory(stored.category);
      if (typeof stored.minAdvCr === 'number') setMinAdvCr(stored.minAdvCr);
      if (VIEW_MODES.has(stored.viewMode)) setViewMode(stored.viewMode);
      if (typeof stored.showHelp === 'boolean') setShowHelp(stored.showHelp);
      if (stored.subType == null || typeof stored.subType === 'string') setSubType(stored.subType);
      if (typeof stored.fnoOnly === 'boolean') setFnoOnly(stored.fnoOnly);
    } catch { /* ignore stale localStorage */ }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('trader-cockpit-theme', theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(STATE_KEY, JSON.stringify({
      view, category, minAdvCr, viewMode, showHelp, subType, fnoOnly,
    }));
  }, [view, category, minAdvCr, viewMode, showHelp, subType, fnoOnly]);

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
