import type { NextConfig } from 'next';

const LIVE_FEED_URL  = process.env.LIVE_FEED_URL  ?? 'http://localhost:8003';
const DATASYNC_URL   = process.env.DATASYNC_URL   ?? 'http://localhost:8001';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      { source: '/datasync/:path*', destination: `${DATASYNC_URL}/api/v1/:path*` },
      { source: '/api/:path*',      destination: `${LIVE_FEED_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
