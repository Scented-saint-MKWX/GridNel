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
- Tailwind + shadcn/ui for primitives, Watermelon UI (`registry.watermelon.sh`, a shadcn-compatible registry) for dashboard blocks — install via `npx shadcn@latest add <registry-url>` rather than hand-building from a blank div. Check the registry for an existing block before writing a component from scratch.
- MapLibre GL JS via `react-map-gl/maplibre` for the map, against CARTO's free tokenless vector tiles — swapped from Mapbox GL 2026-09-13 (no Mapbox account token could be provisioned in the dev environment; see DECISIONS.md #7). No map token env var needed.
- Recharts (or Tremor) for density/corridor-speed charts
- TanStack Query for all data fetching and the 10s `/alerts` polling — one shared hook per resource, not a poller per component
- react-hook-form + zod for the plate-search input
- lucide-react for icons

## Design bar — non-negotiable, both directions

This must not look "vibe-coded" or like a generic AI-generated SaaS template — **and it
must not read as flat/plain either.** "Dark" is not the same as "finished." No default
shadcn gray-on-white with a purple gradient hero, no identical rounded-2xl cards
everywhere, no filler icons, no lorem ipsum. Concrete, checkable requirements, not just
principles:

- **Background needs real depth, not a flat fill.** Near-black base plus an ambient
  treatment — a soft radial gradient mesh (cyan/amber-tinted, very low opacity)
  anchored near a focal point (behind the map, behind the login card), and/or a faint
  grain/noise texture overlay. A single flat `bg-neutral-950` everywhere reads as
  unfinished, not minimal.
- **Glass panels must visibly float, not blend in.** `backdrop-blur-xl`,
  `bg-white/[0.04]`–`bg-white/[0.08]`, a hairline border — plus a soft outer glow tied
  to context (a faint cyan glow under a tracker-surface panel, amber under an active
  alert) so panels read as raised, lit surfaces, not a slightly-lighter rectangle on
  black.
- **Every screen needs a real accent moment**, not monochrome gray-on-black. Role
  colors (amber tracker / cyan analyst / red-amber alerts) should show up in glows,
  active states, chart accents, button treatments — not just a small badge somewhere.
- **`/login` needs presence**, not two buttons on a black screen — an ambient animated
  background, a live "system status" indicator, a properly composed glass card for the
  form.
- **Actually browse `registry.watermelon.sh`'s Dashboards, Auth Templates, and Blocks
  categories and pull real blocks as a starting point for major surfaces** (login
  screen, dashboard shell) rather than hand-building everything from bare shadcn
  primitives — that's the reason Watermelon is in the stack. Restyle its tokens to the
  role-accent system; don't reinvent structure it already provides.
- **Motion must be visible, not theoretical:** hover elevation on glass panels, a live
  pulsing status dot, animated number transitions, the trajectory line drawing in —
  not just "technically has a transition class somewhere."

**Self-audit before calling any screen done — answer these against a real screenshot,
not in the abstract:**
1. Real ambient background treatment, beyond a flat solid fill?
2. Visible depth (shadow/glow) separating panels from background?
3. A role/accent color visibly present, not barely-there?
4. At least one moment of real motion?
5. Conversely — anything here that's decoration with no purpose, or a generic
   template default? Cut it.

If the honest answer to 1–4 is "not really," it's not minimal, it's unfinished — fix it
before moving to new pages.

**Empty/loading states get their own deliberate design, always** — with the real
backend not wired yet, most screens spend most of their time in a no-data state, and a
blank area there reads as unfinished regardless of how good the populated state looks.
Skeleton shimmer for anything about to have real content; for genuinely-no-data states
(no cameras, no alerts yet), use a thematic placeholder — a radar-sweep motif (a slow
rotating conic-gradient sweep, faint, behind "awaiting camera feed" text) fits this
product's domain directly and is not decoration-for-its-own-sake in a surveillance UI.
Never a literally empty rectangle.

## Hard security rules — non-negotiable

- JWT lives in memory (React Context) only. Never `localStorage`, never `sessionStorage`, never a non-httpOnly cookie you set from JS.
- Never put `HMAC_KEY`, `AES_KEY`, or `JWT_SECRET` anywhere in `frontend/` — not in code, not in `.env.local`, not in a comment "for testing." If a task seems to need one of these, stop and flag it instead of proceeding.
- `middleware.ts` is an intentional, commented passthrough — see "Auth gating implementation" below for why and where the real gating lives. Never fetch or render privileged data based solely on a client-side role check; the API's 403 is the actual security boundary.
- URL-encode the plate-text search value and validate its format (zod) before it touches `/track/<text>` or `/track/<text>/bridged`.
- No `dangerouslySetInnerHTML`.
- No secret or internal API detail in a `NEXT_PUBLIC_*` variable — only the API base URL belongs there now (no map token exists to leak; see MapLibre swap above).

## Auth gating implementation & other resolved decisions

See `DECISIONS.md` at the repo root for the full writeup of anything that's already been
settled (auth route-gating with a memory-only JWT, `fog_sim.py` hashing before
`auth/hashing.py` exists, and whatever gets added next). Check it before re-deciding
something that feels ambiguous — it may already be resolved.

**2026-09-13: OD (Origin-Destination) confirmed in-scope, authorized by Wahid** — no
longer an L1 non-goal (TEAM.md §11 updated). It ships as a real, first-class item in
`AnalyticsViewSelector` (`od-flow`), which is a deliberate, flagged deviation from this
file's "exact PS vocabulary" wording elsewhere (Traffic Density / Heatmap / Corridor
Speeds) — a real tradeoff, not a bug. See DECISIONS.md #4 for the full history.

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
