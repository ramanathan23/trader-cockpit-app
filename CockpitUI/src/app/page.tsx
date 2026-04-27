import { CockpitApp } from './CockpitApp';

export const dynamic = 'force-dynamic';

type ServiceConfigs = {
  datasync: Record<string, unknown> | null;
  livefeed: Record<string, unknown> | null;
};

async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

export default async function Page() {
  const DATASYNC_URL  = process.env.DATASYNC_URL  ?? 'http://localhost:8001';
  const LIVE_FEED_URL = process.env.LIVE_FEED_URL ?? 'http://localhost:8003';

  const [datasync, livefeed] = await Promise.all([
    safeFetch<Record<string, unknown>>(`${DATASYNC_URL}/api/v1/config`),
    safeFetch<Record<string, unknown>>(`${LIVE_FEED_URL}/api/v1/config`),
  ]);

  const initialConfigs: ServiceConfigs = { datasync, livefeed };

  return <CockpitApp initialConfigs={initialConfigs} />;
}
