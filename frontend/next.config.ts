import type { NextConfig } from "next";
import path from "path";

const isDev = process.env.NODE_ENV !== "production";

// CSP's connect-src must allow whatever NEXT_PUBLIC_API_URL actually points
// at — hardcoding localhost breaks the moment this deploys anywhere real
// (Vercel + a live API, or even mock mode against a non-local preview URL).
// Falls back to the two local dev origins when the env var is unset, so
// `next dev` against a local API keeps working unchanged.
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
const apiConnectSrc = apiUrl
  ? apiUrl
  : "http://localhost:8000 http://127.0.0.1:8000";

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
// Basemap swapped from Mapbox GL to MapLibre GL against CARTO's free,
// tokenless vector tiles (basemaps.cartocdn.com) — see CityMap.tsx and
// DECISIONS.md. CSP origins updated to match; no api.mapbox.com/tiles.mapbox.com
// left anywhere since nothing loads from Mapbox's infra anymore.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://basemaps.cartocdn.com",
  "worker-src 'self' blob:",
  `connect-src 'self' https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com ${apiConnectSrc}`,
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // NOTE for Vercel: this only helps if Vercel's Root Directory setting is
  // the monorepo root (so ../db is inside what gets uploaded/built). If
  // Root Directory is set to frontend/ (Vercel's usual monorepo pattern),
  // db/cameras.json is outside the deployment entirely and this path can't
  // reach it — see DEPLOYMENT.md for the real constraint and options.
  outputFileTracingRoot: path.join(__dirname, ".."),
  outputFileTracingIncludes: {
    "/api/cameras": ["../db/cameras.json"],
  },
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
