import type { NextConfig } from "next";
import path from "path";

const isDev = process.env.NODE_ENV !== "production";

// script-src keeps 'unsafe-inline' — verified against a real production build
// (not assumed): Next.js's App Router always inlines its RSC hydration payload
// as <script>(self.__next_f=...)</script> tags on every page (7 on /login
// alone), framework-level, present regardless of any app code. Dropping
// 'unsafe-inline' breaks hydration entirely (confirmed: CSP violations, dead
// page). The only real fixes are a nonce + strict-dynamic policy (requires
// converting middleware.ts to proxy.ts and forces every page to dynamic
// rendering — a bigger, team-level tradeoff, see DECISIONS.md §1) or the
// experimental SRI feature. Out of scope for this pass — don't re-attempt
// 'self'-only script-src without one of those. 'unsafe-eval' IS fully dropped
// in production below — Next/React don't need it outside dev's fast-refresh
// machinery, and that part of the tightening is real.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline' https://api.mapbox.com",
  "img-src 'self' data: blob: https://api.mapbox.com https://*.tiles.mapbox.com",
  "worker-src 'self' blob:",
  "connect-src 'self' https://api.mapbox.com https://events.mapbox.com http://localhost:8000 http://127.0.0.1:8000",
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname),
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
