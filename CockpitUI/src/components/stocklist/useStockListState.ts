'use client';

import { useCallback, useState } from 'react';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';

export type StockViewMode = 'table' | 'card' | 'chart' | 'cluster' | 'heatmap';

export function useStockListState() {
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [modalSymbol,    setModalSymbol]    = useState<string | null>(null);
  const [modalTab,       setModalTab]       = useState<SymbolModalTab>('details');
  const [viewMode,       setViewMode]       = useState<StockViewMode>('table');
  const [showPresets,    setShowPresets]    = useState(false);

  const toggleExpand = useCallback((symbol: string) => {
    setExpandedSymbol(prev => prev === symbol ? null : symbol);
  }, []);

  const openModal = useCallback((symbol: string, tab: SymbolModalTab = 'details') => {
    setModalSymbol(symbol);
    setModalTab(tab);
  }, []);

  const closeModal = useCallback(() => setModalSymbol(null), []);

  return {
    expandedSymbol, toggleExpand,
    modalSymbol, modalTab, openModal, closeModal,
    viewMode, setViewMode,
    showPresets, setShowPresets,
  };
}
