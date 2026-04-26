'use client';

import { useEffect, useState } from 'react';

export interface EChartColors {
  base: string;
  panel: string;
  card: string;
  lift: string;
  border: string;
  rim: string;
  fg: string;
  dim: string;
  ghost: string;
  accent: string;
  bull: string;
  bear: string;
  amber: string;
  sky: string;
}

const FALLBACK: EChartColors = {
  base: '#0a0c0e',
  panel: '#121518',
  card: '#181c20',
  lift: '#1f252a',
  border: '#2f383f',
  rim: '#56646e',
  fg: '#eaeef0',
  dim: '#a0acb2',
  ghost: '#6d7c84',
  accent: '#22998b',
  bull: '#0db176',
  bear: '#e5495d',
  amber: '#de9748',
  sky: '#4399d8',
};

function cssColor(name: keyof EChartColors): string {
  if (typeof window === 'undefined') return FALLBACK[name];
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  return value ? `rgb(${value})` : FALLBACK[name];
}

function readColors(): EChartColors {
  return {
    base: cssColor('base'),
    panel: cssColor('panel'),
    card: cssColor('card'),
    lift: cssColor('lift'),
    border: cssColor('border'),
    rim: cssColor('rim'),
    fg: cssColor('fg'),
    dim: cssColor('dim'),
    ghost: cssColor('ghost'),
    accent: cssColor('accent'),
    bull: cssColor('bull'),
    bear: cssColor('bear'),
    amber: cssColor('amber'),
    sky: cssColor('sky'),
  };
}

export function useEChartColors(): EChartColors {
  const [colors, setColors] = useState<EChartColors>(FALLBACK);

  useEffect(() => {
    setColors(readColors());
    const observer = new MutationObserver(() => setColors(readColors()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  return colors;
}

