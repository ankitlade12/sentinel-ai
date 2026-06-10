/** @type {import('next').NextConfig} */

// All client calls hit /api/* same-origin; Next proxies to the FastAPI backend.
// Local dev: http://localhost:8000. In docker-compose: http://backend:8000.
const apiTarget = process.env.SENTINEL_API_TARGET || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiTarget}/api/:path*` }];
  },
};

export default nextConfig;
