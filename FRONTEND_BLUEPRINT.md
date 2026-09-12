# SentinelGrid — Frontend (P2) End-to-End Blueprint

**Owner:** Wahid (P2) — `frontend/`, `fog-node/fog_sim.py`, `scripts/replay.py`, demo script
**Status:** Draft for team review. **TEAM.md remains the single source of truth.** Nothing here overrides a frozen contract in TEAM.md §4. Where this document adds detail, it's additive; where it disagrees, TEAM.md wins and this file needs to be updated, not the reverse.

## Repo state as of 2026-09-12 (verified directly on disk, not guessed)

- `TEAM.md` and `README.md` were 0 bytes in this repo until just now — the content above/below assumes the real TEAM.md text is present; if you're reading this and TEAM.md is empty again, stop and get the real content before trusting anything else in this file.
- `frontend/` already has the full skeleton this document describes below — `app/(protected)/{tracking,analytics}`, `components/{alerts,analytics,layout,map}`, `hooks/`, `lib/`, `types/`, `middleware.ts`, `next.config.ts`, `package.json`, `tsconfig.json` — but every file is a 0-byte placeholder. This is a shape to fill in, not a shape to invent. Do not run `create-next-app` over it blindly; populate the existing files directly, or scaffold in a scratch dir and merge in.
- **Unresolved anomaly:** `frontend/fog-node/buffer.py` + `frontend/fog-node/data/buffer.db` exist, nested inside `frontend/`, and match nothing in TEAM.md. Also empty. Do not build this out or delete it without asking the team what it's for — it may be a stray duplicate of the top-level `fog-node/` folder, or an undocumented idea.

---

## 0. Direct answer: does your file structure work?

Mostly, but it's a skeleton, not a build plan. Two real gaps:

1. **It has no auth/role-gating mechanism.** You need "dashboard → both pages, but tracking is privileged-only" — that's a specific Next.js pattern (route groups + middleware), not just folders. Missing this is the difference between "looks done" and "is actually gated."
2. **It's missing the plumbing that makes a Next.js app maintainable under a deadline:** no `lib/` (API client, token handling), no `types/` (your data contracts as code), no `middleware.ts`, no frontend `.env.local`. Without these, Claude Code will improvise its own conventions per file, and by hour 20 you'll have three different ways of calling the API.

Section 2 below gives you the corrected tree. Everything else in your paste (`api/`, `db/`, `fog-node/`, `auth/`) matches TEAM.md fine — that's not your lane, leave it alone.

One more thing worth knowing: the correction note about the architecture PDF (raw video → JPEG snapshot) is **already correctly reflected in TEAM.md's diagram and Data Block** (`cam_event_id`, no raw video anywhere in the contract). Nothing to fix there — it was a diagram bug, not a contract bug.

---

## 1. Frozen contracts you are building against (do not deviate)

Copied verbatim from TEAM.md §4 so Claude Code never has to guess or invent a shape.

**Endpoints you consume:**
```
POST /login                       {username, password} → JWT {sub, role}
GET  /alerts?since=...             both roles; polling only, NO WebSocket, 10s interval
GET  /track/<plate_text>           tracker role only
GET  /track/<plate_text>/bridged   tracker role only; adds A*-inferred gap segments
POST /blacklist                    tracker role only {plate_text, reason}
DELETE /blacklist/<plate_hash>     tracker role only
GET  /analytics/density?hours=1    analyst role; per-camera counts
GET  /analytics/heatmap?hours=1    analyst role; [{lat, lon, weight}]
GET  /analytics/corridor-speeds    analyst role; per-edge avg implied speed
GET  /debug/hash/<text>            tracker role only; demo helper
```

**Trajectory response shape** (`/track/*`):
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

**Roles:** `tracker` (privileged — tracking + blacklist) and `analyst` (unprivileged — analytics only). Analyst responses get `plate_text_enc` stripped server-side — you will never see it, so don't build UI that expects it.

**Cameras:** six, two zones, from `db/cameras.json` — nobody hardcodes camera positions, including the frontend. Fetch or import this file at build/runtime; never paste coordinates into a component.

**Demo credentials (per TEAM.md §7):** `tracker/track123`, `analyst/analytics123`.

---

## 2. Corrected `frontend/` tree

```
frontend/
├── Dockerfile
├── package.json
├── tsconfig.json
├── next.config.ts
├── .env.local.example        # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_MAPBOX_TOKEN — nothing secret
├── middleware.ts             # role-gate at the edge, before a page ever renders
├── types/
│   ├── auth.ts               # JWT payload {sub, role, exp}
│   ├── tracking.ts           # Trajectory + segment types, mirrors §4.4 exactly
│   └── analytics.ts          # density / heatmap / corridor-speed response types
├── lib/
│   ├── api.ts                # fetch wrapper: attaches JWT, centralizes 401/403 handling
│   ├── auth.ts                # token get/set (in-memory), decode/expiry check
│   └── cameras.ts             # loads db/cameras.json once, typed
├── hooks/
│   ├── useAlerts.ts           # TanStack Query, 10s polling on /alerts
│   ├── useTrajectory.ts       # /track/<text>/bridged query
│   └── useAnalytics.ts        # density/heatmap/corridor-speeds queries
├── app/
│   ├── layout.tsx             # root layout, providers (QueryClient, AuthProvider)
│   ├── login/
│   │   └── page.tsx           # role picker → POST /login
│   └── (protected)/
│       ├── layout.tsx         # dashboard shell: nav, alert console, role check
│       ├── tracking/
│       │   └── page.tsx       # PRIVILEGED — server-checked in middleware + re-checked here
│       └── analytics/
│           └── page.tsx       # both roles
├── components/
│   ├── ui/                    # shadcn + Watermelon UI primitives, untouched copy-paste output
│   ├── map/
│   │   ├── CityMap.tsx        # Mapbox wrapper, camera markers from cameras.json
│   │   ├── TrajectoryLayer.tsx# solid=observed, dashed=inferred polylines
│   │   └── HeatmapLayer.tsx
│   ├── alerts/
│   │   └── AlertConsole.tsx   # red banner + camera flash, polling-driven
│   ├── analytics/
│   │   ├── DensityChart.tsx
│   │   └── CorridorSpeedChart.tsx
│   └── layout/
│       ├── Navbar.tsx
│       └── RoleBadge.tsx
└── public/
```

**Why this shape:** `middleware.ts` + the `(protected)` route group is the actual mechanism behind your requirement ("both pages need auth, tracking needs privilege"). `lib/api.ts` is the one place a 401/403 gets handled, so you're not writing try/catch around every fetch. `types/` mirrors the contracts in Section 1 so a backend change to the shape is a one-file diff, not a hunt through components.

---

## 3. Tech stack — all $0, all justified

| Concern | Choice | Why |
|---|---|---|
| Framework | Next.js (App Router) + TypeScript | You already committed to this in TEAM.md; App Router's route groups + `middleware.ts` are the cleanest fit for role-gating. |
| Styling / components | Tailwind + **shadcn/ui** (primitives: button, input, dialog, table) + **Watermelon UI** (dashboard blocks, forms, layouts) | Both are copy-paste, MIT-licensed, own-your-code registries — zero recurring cost, no vendor lock-in. Watermelon is *built on* shadcn + Radix, so they compose directly; you install Watermelon blocks the same way you install shadcn components (`npx shadcn@latest add <registry-url>`), because Watermelon publishes itself as a shadcn-compatible registry. This is what gets you "visually pleasing" without hand-building every component from a blank div. |
| Maps | Mapbox GL JS (`react-map-gl`) | Free tier is 50,000 map loads/month with no credit card — a hackathon demo won't come close. If token setup becomes a blocker on demo day, MapLibre GL JS (a permissive fork, same API) + free OSM tiles is a zero-signup fallback — keep this as Plan B, not Plan A, since TEAM.md already names Mapbox. |
| Charts | Recharts (or Tremor, which wraps Recharts for dashboard-shaped components) | Free, MIT, lightweight, plays well with Tailwind. Use for density + corridor-speed bar/line charts; the heatmap itself renders as a Mapbox layer, not a chart-library heatmap. |
| Data fetching / polling | TanStack Query | `refetchInterval` gives you the 10s `/alerts` polling TEAM.md specifies for free, plus caching and retry — don't hand-roll `setInterval`. |
| Auth state | React Context, in-memory only | See Section 4 — no Redux needed for a two-role, few-page app. |
| Forms / validation | react-hook-form + zod | Validate the plate-text input client-side (format, length) before it ever hits `/track/<text>` — cheap defense and better UX. |
| Icons | lucide-react | Ships with shadcn by default, MIT. |
| Hosting | None required | The demo runs via `docker compose up` per TEAM.md §5/§8; frontend is one more service in that compose file. A public Vercel deployment is optional polish, not a requirement — skip it unless you have spare hours after rehearsal. |

---

## 4. Auth & role-gating — the core of your requirement

### 4.1 Flow

```
User → /login → POST /login {username,password}
                     │
                     ▼
              {sub, role, exp} JWT returned in response body
                     │
                     ▼
       stored in React Context (memory only — see 4.3)
                     │
                     ▼
    navigate to /(protected)/... → middleware.ts runs FIRST
                     │
        ┌────────────┴────────────┐
        │                         │
   no valid token           valid token
        │                         │
   redirect → /login      role == tracker?  → /tracking allowed
                           role == analyst? → /tracking → redirect to /analytics
                           either role       → /analytics allowed
```

### 4.2 Where the check actually happens (defense in depth — do both, not either)

1. **`middleware.ts`** — reads the token, decodes the role claim, redirects before the page ever renders. This is what makes the UI *feel* gated and stops accidental exposure of the tracking UI shell to an analyst.
2. **The API's 403** (already built by P4/P5 per TEAM.md §4.4/§8) — this is the *real* gate. **Never treat the frontend check as the security boundary.** If middleware has a bug, the worst case must still be "API returns 403, page shows an error" — never "analyst sees plate data because the button rendered."

Tell Claude Code explicitly: frontend role checks are UX, not security. Written into CLAUDE.md as a hard rule.

### 4.3 Token storage: memory, not localStorage

TEAM.md says "memory preferred, localStorage acceptable demo" — go with memory. Reasoning: `localStorage` is readable by any script on the page, so any dependency-supply-chain issue (a compromised npm package) or XSS in a chart/map library gets your JWT for free. In-memory (React Context, lost on refresh) has one real cost — a hard refresh mid-demo logs you out — which is a rehearsal problem, not a security problem. Solve it by rehearsing, not by weakening storage.

**Stretch improvement worth raising with Nawfal/Krishna (not required, doesn't break the frozen response shape):** have `/login` also set an `httpOnly`, `Secure`, `SameSite=Strict` cookie alongside the JSON body. That removes the "lost on refresh" problem entirely and is materially more secure, since it's invisible to JS/XSS altogether. This is additive to the existing contract, not a breaking change — worth a two-line proposal in the group chat, not a unilateral change.

### 4.4 Session expiry mid-demo

Ask Krishna what `exp` is set to. Whatever it is, know it, and make sure the demo (≈5 minutes per TEAM.md §13) fits inside it with margin. Log in fresh immediately before walking on stage, not at hour 30 during rehearsal.

---

## 5. Page-by-page spec

### `/login`
- Role picker (two buttons or a toggle: Tracker / Analyst) — pre-fills nothing sensitive, just shapes the login form per TEAM.md's demo credentials.
- On success: store token in context, route to `/analytics` by default (safe for both roles) — never auto-route to `/tracking`, even for a tracker login, since that's a privileged surface and shouldn't be the reflexive landing page.

### `/(protected)/layout.tsx` — the dashboard shell
- Persistent nav (Tracking / Analytics links — hide the Tracking link entirely for analysts, on top of the middleware redirect; hiding it is UX politeness, the middleware/API are the actual gate).
- Mounts `AlertConsole` globally so a blacklist hit is visible no matter which page you're on — this is one of the five demo beats and must not be tucked away on a sub-page.

### `/tracking` (privileged only)
- Plate-text search box (zod-validated format before submit).
- `CityMap` with camera markers from `cameras.json`.
- On search: call `/track/<text>/bridged`, render `TrajectoryLayer` — **solid polyline for `type:"observed"` segments, dashed for `type:"inferred"`** (TEAM.md §8, P2 spec, verbatim requirement).
- Camera markers show timestamp + `outcome` on click.
- Segments with `"healed": true` get a visible "self-corrected misread" badge — this is a specific demo beat (bridging + self-heal), don't let it render identically to a normal segment.
- A `/debug/hash/<text>` helper call (tracker-only) so you can show the judges the plaintext→hash link live, per TEAM.md.

### `/analytics` (both roles)
- Dropdown using PS vocabulary exactly: **Traffic Density / Heatmap / Corridor Speeds** (TEAM.md is explicit that this vocabulary matters for judges).
- Density → bar/line chart per camera × hour bucket.
- Heatmap → Mapbox heat layer, not a chart-library heatmap.
- Corridor speeds → per-edge chart.

### Alert console (global, not a page)
- Polls `/alerts?since=...` every 10s via `useAlerts`.
- Blacklist hit → red banner + the specific camera marker flashes on whatever map is currently mounted.

---

## 6. `fog_sim.py` + `replay.py` + demo script — your other half of P2

Easy to forget these live in your lane too. Recap from TEAM.md so nothing falls through:

- **`fog_sim.py`**: Mode A (instant mock, unblocks P4 at hour 3 — fabricated blocks matching §4.1 exactly, no real OCR) and Mode B (real pipeline, hour 16+, once P1's `pipeline.py` exists). Injections at hour 16-26: p≈0.05 blacklisted plate, p≈0.10 one-char vendor misread (to show `engine_preferred` fusion live), p≈0.05 low-confidence drop.
- **`replay.py`**: records a good run, re-drives it in identical order/timing. **The demo runs on replay, not live mode** — live mode is the flourish if time allows. This determinism requirement means: no randomness in the *replayed* run, only in the *recorded* run that produced it.
- **Demo script** (TEAM.md §13, you own the final cut): 30s compose boot → 60s live sim → 30s blacklist beat → 90s tracking beat (search + one bridged gap + one healed segment) → 60s analytics beat (logout/login as analyst, showing privilege separation) → 45s privacy beat (sweeper + audit log) → 45s close. Every page you build has to visibly support one of these beats — if a feature doesn't show up in this script, it's not worth building before hour 26.

---

## 7. Security checklist — frontend-specific, end to end

- [ ] JWT in memory only, never `localStorage`/`sessionStorage` (Section 4.3).
- [ ] `middleware.ts` gates routes, but the API's 403 is the real boundary — no privileged data ever fetched client-side before a role check passes.
- [ ] Plate-text input validated (regex/length via zod) before it's interpolated into a URL path — also URL-encode it regardless.
- [ ] No secrets in `NEXT_PUBLIC_*` env vars — only the Mapbox token (which is meant to be public/domain-scoped) and the API base URL belong there. `HMAC_KEY`, `AES_KEY`, `JWT_SECRET` never touch the frontend at all, per TEAM.md §4.2 — if Claude Code ever asks for one of these to "test something," that's a sign to stop and check in with P5, not to paste it in.
- [ ] No `dangerouslySetInnerHTML` anywhere; React's default JSX escaping is your XSS defense — don't work around it for convenience.
- [ ] A basic CSP via `next.config.ts` headers (restrict `script-src` to self + Mapbox's CDN) — cheap insurance, ask Claude Code to verify current Next.js header config syntax since this shifts between versions.
- [ ] `npm audit` run before freeze (hour 26) — fix or consciously accept, don't ignore silently.
- [ ] Logout actually clears the in-memory token and any TanStack Query cache holding privileged data (`queryClient.clear()`), not just a redirect.

---

## 8. Hour-by-hour plan — your (P2) lane inside TEAM.md's global clock

| Hour | Global checkpoint | Your deliverable |
|---|---|---|
| 0–3 | Checkpoint 1: contracts frozen | Next.js boots, routes stubbed, `cameras.json` consumed, `fog_sim.py` v0 emitting fabricated §4.1 blocks (unblocks P4 today) |
| 3–12 | Checkpoint 2: mock block on the real map | `CityMap` with real camera markers; `/track` polyline against fake/mocked data; login flow wired to real `/login` |
| 12–16 | Checkpoint 3: full compose stack | Analytics page (dropdown + chart + heatmap layer); alert console with 10s polling |
| 16–26 | Demo features | Bridged/dashed segments + healed badge; `fog_sim.py` mode B + injections; **`replay.py` recording a good run**; sim injections wired |
| 26–31 | Freeze + rehearsal | No new features. Demo script finalized, rehearsed twice end-to-end. Fresh-clone test (your part: does `frontend/` boot clean from `docker compose up` with only `.env.example` copied?) |
| 31–36 | Buffer | Only if rehearsed twice — never touch the five demo beats |

---

## 9. Loophole / failure audit — what actually kills a frontend demo

| Risk | Why it happens | Mitigation |
|---|---|---|
| Mapbox token exposed/rate-limited on demo day | Token hardcoded instead of env var, or a public repo leak | `NEXT_PUBLIC_MAPBOX_TOKEN` from `.env.local`, never committed; scope the token to your domain/localhost in Mapbox's dashboard |
| JWT expires mid-demo | Nobody checked `exp` | Section 4.4 — know the value, log in fresh right before presenting |
| Analyst UI flashes privileged data for a frame before redirect | Only checking role in a `useEffect` client-side, after first render | `middleware.ts` runs before render — use it, don't rely solely on client-side checks |
| Polling storm / rate limiting | Multiple components each polling `/alerts` independently | One `useAlerts` hook, shared via TanStack Query cache, not one poller per component |
| "Works on my machine" | Manual `npm install` outside compose, undocumented env var | Fresh-clone test is P5's gate at hour 28 (TEAM.md) — make sure `frontend/` participates, not just the backend services |
| Demo breaks because live mode misbehaves | Live mode depends on real-time timing that isn't reproducible | Demo runs on `replay.py`, always — live mode is the flourish, never the backbone (Section 6) |

---

## 10. Definition of done — P2 (frontend), on top of TEAM.md §15

- [ ] `/login` → role-correct landing, both demo accounts work
- [ ] `/tracking` unreachable (redirected) for `analyst` role — provable live, both via UI redirect and via a direct API 403 if someone bypasses the UI
- [ ] Bridged trajectory shows solid + dashed segments and at least one "healed" badge
- [ ] Analytics dropdown shows Density / Heatmap / Corridor Speeds in that vocabulary, both roles can reach it
- [ ] Alert console fires within 10s of a blacklist hit, from any page
- [ ] `replay.py` produces an identical, timed run every time it's invoked
- [ ] `docker compose up` from a fresh clone boots `frontend/` cleanly with only `.env.example` copied
- [ ] No secret ever appears in frontend source, bundle, or `NEXT_PUBLIC_*` vars
- [ ] Demo rehearsed twice, you know which beats you narrate
