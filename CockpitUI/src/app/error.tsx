'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[GlobalError]', error);
  }, [error]);

  return (
    <div className="h-screen flex flex-col items-center justify-center gap-4 bg-base text-fg">
      <span className="text-[13px] text-bear font-bold">Something went wrong</span>
      <span className="text-[11px] text-ghost max-w-md text-center">{error.message}</span>
      <button
        onClick={reset}
        className="px-4 py-1.5 text-[11px] font-bold bg-accent/20 text-accent rounded hover:bg-accent/30 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
