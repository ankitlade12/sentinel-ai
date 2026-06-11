/** @type {import('next').NextConfig} */

// /api/* is proxied to the FastAPI backend at RUNTIME by the catch-all route
// handler in app/api/[...path]/route.ts (reads SENTINEL_API_TARGET per request).
// We deliberately do NOT use next.config rewrites here, because their
// destination is baked at build time and can't be set from a Cloud Run env var.
const nextConfig = {
  output: "standalone",
};

export default nextConfig;
