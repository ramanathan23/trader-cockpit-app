import type { NextConfig } from 'next';

const LIVE_FEED_URL = process.env.LIVE_FEED_URL ?? 'http://localhost:8003';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${LIVE_FEED_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
