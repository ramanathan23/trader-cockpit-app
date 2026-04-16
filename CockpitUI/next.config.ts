import type { NextConfig } from 'next';

const LIVE_FEED_URL = process.env.LIVE_FEED_URL ?? 'http://localhost:8003';
const SCORER_URL    = process.env.SCORER_URL    ?? 'http://localhost:8002';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      // MomentumScorerService routes
      { source: '/scorer/:path*', destination: `${SCORER_URL}/api/v1/:path*` },
      // LiveFeedService (default for all /api/* routes)
      { source: '/api/:path*',    destination: `${LIVE_FEED_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
