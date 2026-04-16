'use client';

import { useEffect, useState } from 'react';

export function useClock() {
  const [clock, setClock] = useState('--:--:--');

  useEffect(() => {
    const tick = () => {
      const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
      setClock(ist.toTimeString().slice(0, 8));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return clock;
}
