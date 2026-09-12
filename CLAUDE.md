# CLAUDE.md — SentinelGrid Frontend (P2)

This file is for Claude Code. `TEAM.md` at the repo root is the absolute source of truth for the whole project — if anything here conflicts with it, `TEAM.md` wins and this file is wrong and needs fixing. `FRONTEND_BLUEPRINT.md` is your detailed execution plan; this file is the short, load-every-session version.

## Your scope

You own and may freely edit:
```
frontend/
fog-node/fog_sim.py
scripts/replay.py
```
You may **read** anything else in the repo for context (especially `TEAM.md`, `db/cameras.json`, `api/schemas.py`) but do not edit `db/`, `api/`, `auth/`, `fog-node/pipeline.py`, `fog-node/enhance.py`, or `fog-node/ocr.py` — those belong to teammates (P1/P3/P4/P5). If a task seems to require changing one of those, stop and say so instead of doing it.

**Known anomaly — do not build on this without asking:** there is a second, unexpected `fog-node/` folder nested inside `frontend/` (`frontend/fog-node/buffer.py`, `frontend/fog-node/data/buffer.db`). It matches nothing in TEAM.md and nothing in this file. Leave it alone and flag it to the team instead of guessing what it's for.

## Frozen contracts — never invent, never deviate

**Endpoints you call** (exact paths, exact roles):
```
POST /login                       {username, password} → JWT {sub, role}
GET  /alerts?since=...             both roles; poll every 10s, NO WebSocket
GET  /track/<plate_text>           tracker only
GET  /track/<plate_text>/bridged   tracker only
POST /blacklist                    tracker only {plate_text, reason}
DELETE /blacklist/<plate_hash>     tracker only
GET  /analytics/density?hours=1    analyst
GET  /analytics/heatmap?hours=1    analyst
GET  /analytics/corridor-speeds    analyst
GET  /debug/hash/<text>            tracker only
```

**Trajectory response shape** (do not add/rename/remove fields when typing this):
```json
{
  "plate": "MH12AB1284",
  "segments": [
    {"type":"observed","camera_id":"CAM_01","ts":"...","lat":0,"lon":0,"outcome":"agreement"},
    {"type":"inferred","from":"CAM_01","to":"CAM_03","ts_start":"...","ts_end":"...",
     "path":[[lon,lat]],"algorithm":"astar_speed_prior"},
    {"type":"observed","camera_id":"CAM_03","ts":"...","lat":0,"lon":0,"healed":false}
  ]
}
```

Roles are `tracker` and `analyst`. Analyst responses never contain `plate_text_enc` — don't build UI that expects it, don't add a fallback for it.

## Tech stack (do not substitute without asking)

- Next.js (App Router) + TypeScript, strict mode on
- Tailwind + shadcn/ui for primitives, Watermelon UI (`ui.watermelon.sh`, a shadcn-compatible registry) for dashboard blocks — install via `npx shadcn@latest add <registry-url>` rather than hand-building from a blank div. Check the registry for an existing block before writing a component from scratch.
- Mapbox GL JS via `react-map-gl` for the map (token from `NEXT_PUBLIC_MAPBOX_TOKEN`)
- Recharts (or Tremor) for density/corridor-speed charts
- TanStack Query for all data fetching and the 10s `/alerts` polling — one shared hook per resource, not a poller per component
- react-hook-form + zod for the plate-search input
- lucide-react for icons

## Design bar — non-negotiable

This must not look "vibe-coded" or like a generic AI-generated SaaS template. No default shadcn gray-on-white with a purple gradient hero, no identical rounded-2xl cards everywhere, no filler icons, no lorem ipsum. Build a dark-first "traffic-ops command center" look: real glassmorphism (`backdrop-blur-xl`, `bg-white/[0.04]`–`bg-white/[0.08]`, hairline `border-white/10`), purposeful role-tied accent colors (alerts, tracker, analyst each get their own), a monospace face reserved for data values (plate numbers, hashes, timestamps) paired with a clean sans for UI chrome, and a map that gets real screen space instead of being squeezed into a card. Before calling any UI task done, actually look at it rendered and ask whether it looks like a template or a purpose-built product.

## Hard security rules — non-negotiable

- JWT lives in memory (React Context) only. Never `localStorage`, never `sessionStorage`, never a non-httpOnly cookie you set from JS.
- Never put `HMAC_KEY`, `AES_KEY`, or `JWT_SECRET` anywhere in `frontend/` — not in code, not in `.env.local`, not in a comment "for testing." If a task seems to need one of these, stop and flag it instead of proceeding.
- `middleware.ts` is an intentional, commented passthrough — see "Auth gating implementation" below for why and where the real gating lives. Never fetch or render privileged data based solely on a client-side role check; the API's 403 is the actual security boundary.
- URL-encode the plate-text search value and validate its format (zod) before it touches `/track/<text>` or `/track/<text>/bridged`.
- No `dangerouslySetInnerHTML`.
- No secret or internal API detail in a `NEXT_PUBLIC_*` variable — only the Mapbox token and the API base URL belong there.

## Auth gating implementation & other resolved decisions

See `DECISIONS.md` at the repo root for the full writeup of anything that's already been
settled (auth route-gating with a memory-only JWT, `fog_sim.py` hashing before
`auth/hashing.py` exists, and whatever gets added next). Check it before re-deciding
something that feels ambiguous — it may already be resolved.

## Definition of done for any frontend task

- `tsc --noEmit` and lint pass
- The page/component actually enforces the role split described above (privileged vs both-roles), not just visually — verify by trying to reach `/tracking` as `analyst` and confirming a redirect
- No hardcoded camera coordinates — read from `db/cameras.json`
- If you added a UI library component, it came from shadcn/Watermelon's registry, not hand-rolled, unless nothing in the registry fits
- Demo credentials still work: `tracker/track123`, `analyst/analytics123`

## Git

Personal branch (`wahid/frontend`), PR at the three checkpoints (hour 3 / 12 / 16 per TEAM.md). After hour 16, direct commits to `main` are for bugfixes only. Don't touch `TEAM.md` without team agreement.

## When stuck

Post in the team chat with what you tried (TEAM.md §12's rule) rather than guessing silently at a contract detail — a wrong guess here (e.g. inventing a field on the trajectory response) breaks P4's actual API contract, not just your UI.
