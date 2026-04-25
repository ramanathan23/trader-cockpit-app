import { CockpitApp } from './CockpitApp';

export const dynamic = 'force-dynamic';

type ServiceConfigs = {
  scorer:   Record<string, unknown> | null;
  datasync: Record<string, unknown> | null;
  livefeed: Record<string, unknown> | null;
  modeling: Record<string, unknown> | null;
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
  const SCORER_URL   = process.env.SCORER_URL   ?? 'http://localhost:8002';
  const DATASYNC_URL = process.env.DATASYNC_URL ?? 'http://localhost:8001';
  const LIVE_FEED_URL= process.env.LIVE_FEED_URL?? 'http://localhost:8003';
  const MODELING_URL = process.env.MODELING_URL ?? 'http://localhost:8004';

  const [scorer, datasync, livefeed, modeling] = await Promise.all([
    safeFetch<Record<string, unknown>>(`${SCORER_URL}/api/v1/config`),
    safeFetch<Record<string, unknown>>(`${DATASYNC_URL}/api/v1/config`),
    safeFetch<Record<string, unknown>>(`${LIVE_FEED_URL}/api/v1/config`),
    safeFetch<Record<string, unknown>>(`${MODELING_URL}/api/v1/config`),
  ]);

  const initialConfigs: ServiceConfigs = { scorer, datasync, livefeed, modeling };

  return <CockpitApp initialConfigs={initialConfigs} />;
}
