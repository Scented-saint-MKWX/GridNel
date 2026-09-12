# Frontend — Vercel Deployment Notes (P2)

Prep work only, per the Phase 6 master prompt Part 3 — **not deployed**. This
documents what's needed and one real constraint that needs a team decision
before deploying for real.

## Environment variables (set in Vercel's dashboard, Project Settings → Environment Variables)

| Variable | Controls | Required? |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL the frontend calls for every non-mock request (`/login`, `/track/*`, `/alerts`, `/analytics/*`). Also widens the CSP's `connect-src` to match — see below. | Yes, unless `NEXT_PUBLIC_MOCK_MODE=true` |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox GL JS access token for `CityMap` and every map layer. Without it, every screen still renders (empty-state fallback), but no map ever draws. Scope the token to the deployed domain in Mapbox's dashboard. | Yes, for the map to actually work |
| `NEXT_PUBLIC_MOCK_MODE` | `true` routes every `apiFetch` call through `lib/mock/router.ts` fixtures instead of a real backend — this is what makes a public demo work with no backend reachable. Always shows the amber "MOCK DATA" banner (`MockBanner.tsx`) when on. Default is `false`; never leave a public deployment on `true` by accident. | No — defaults to `false` |

None of `HMAC_KEY`, `AES_KEY`, `JWT_SECRET`, or `FOG_API_KEY` belong here — those are backend-only (TEAM.md §4.2) and must never be set on the frontend Vercel project, even as non-`NEXT_PUBLIC_` vars.

## What was checked/fixed for Vercel compatibility

1. **CSP `connect-src` no longer hardcodes localhost.** `next.config.ts` previously allowed only `http://localhost:8000` and `http://127.0.0.1:8000` for API calls — on any real deployment this would silently block every fetch to a real `NEXT_PUBLIC_API_URL`. It now derives `connect-src` from `NEXT_PUBLIC_API_URL` at build time (falling back to the two local origins only when that var is unset, so `next dev` is unaffected).

2. **Production build verified clean.** `npm run build` compiles, type-checks, lints, and generates all routes with no errors (`/`, `/login`, `/(protected)/tracking`, `/(protected)/analytics`, `/api/cameras`, middleware).

## Real constraint that needs a team decision before deploying for real

**`db/cameras.json` lives outside `frontend/`, at the monorepo root** (TEAM.md §4.3 — shared by the DB seeder, `fog_sim.py`, and the frontend). `app/api/cameras/route.ts` reads it via a relative filesystem path (`lib/cameras.ts`), which works locally because the whole monorepo is on disk together.

Vercel's standard monorepo pattern sets the project's **Root Directory** to `frontend/` — meaning only `frontend/` and its contents are uploaded and built. If that's how this gets configured, `../db/cameras.json` is **outside the deployment entirely** and `/api/cameras` will always return `[]` (the code fails closed to the existing empty-state UI, not a crash — but cameras will never load).

`next.config.ts` now sets `outputFileTracingRoot` one level up (the monorepo root) and explicitly lists `../db/cameras.json` in `outputFileTracingIncludes` for the `/api/cameras` route — verified working in a local production build (the trace manifest correctly includes `db/cameras.json`). **This only fixes the problem if Vercel's Root Directory is also set to the monorepo root**, not `frontend/`.

Three options, not decided here:
- Set Vercel's Root Directory to the repo root and point its build command/output at `frontend/` (keeps one source of truth for `cameras.json`, matches what's now configured).
- Duplicate/symlink `cameras.json` into `frontend/` at deploy time via a build step (adds a sync step, avoids the Root Directory constraint).
- Have the frontend fetch `cameras.json` from the real backend once `GET /cameras` (or similar) exists there, instead of reading the file directly — removes the filesystem dependency entirely, but isn't in TEAM.md §4.4 today.

Don't pick one unilaterally — this touches how the monorepo deploys as a whole, not just `frontend/`.

## Not done (explicitly out of scope for this pass)

- No actual deployment was triggered — prep only, per the master prompt's explicit instruction not to deploy without asking first.
- No Vercel project was created or connected.
