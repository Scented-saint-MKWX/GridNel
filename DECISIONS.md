# GridNel Frontend — Resolved Decisions Log (P2)

Short-lived architectural questions that came up mid-build, resolved here so they
don't get re-litigated in a later session or lost when context resets. `CLAUDE.md`
points here — check this file when something feels ambiguous before re-deciding it.

---

## 1. Auth route-gating: `middleware.ts` can't see an in-memory JWT (resolved 2026-09-12)

**Problem:** `middleware.ts` runs on the edge/server; the JWT lives only in a client-side
React Context per the memory-only rule. Middleware structurally cannot decode a role
claim it never receives.

**Resolution:**
- `middleware.ts` stays an intentional, commented passthrough — comment explains why,
  so nobody "fixes" it later by adding a cookie.
- Real UX-level gating happens in `(protected)/layout.tsx` as a hydration guard: render
  nothing but a loading skeleton (no map, no data fetch, no privileged markup) until
  `AuthProvider` resolves whether a valid `{sub, role, exp}` exists in memory, then
  either redirect or render children.
- `tracking/page.tsx` repeats a lightweight role check itself as defense-in-depth.
- **Do not add any cookie**, including a role-only one, to make middleware "work" —
  that's a real exception to the memory-only rule bought for a cosmetic win. The
  correct upgrade path, if wanted later, is asking P5 for an httpOnly
  `Secure SameSite=Strict` JWT cookie alongside `/login`'s existing JSON body
  (additive, doesn't change the frozen response shape) — strictly more secure than
  memory *and* survives refresh. Team decision, not a unilateral one.

---

## 2. `fog_sim.py` needs hashing before `auth/hashing.py` exists (resolved 2026-09-12)

**Problem:** mode A must emit `plate_hash` (HMAC) and `plate_text_enc` (AES) per the
frozen Data Block (TEAM.md §4.1), but `auth/hashing.py` (P5's file, imported by
api/fog-node/seeder per TEAM.md §8) is still empty, and writing crypto logic isn't
P2's lane.

**Resolution:** `fog_sim.py` imports `auth.hashing` normally. If the import fails, or
the functions raise `NotImplementedError` (P5 hasn't landed real crypto yet), fall back
to a **local placeholder with the identical function signature** — never anything that
resembles a real hash (TEAM.md §11 bans weak/plain hashing patterns; the placeholder
shouldn't even superficially look like one):
- placeholder `hmac_plate(text)` → `"unhashed::" + text` (deterministic — same plate
  text always produces the same placeholder, so multi-camera matching is still
  testable)
- placeholder `encrypt_plate(text)` → `base64("PLACEHOLDER::" + text)`
- Print a loud one-time startup warning whenever the fallback path is active.

Rejected: literally importing and letting it `ImportError` until P5 lands the real
file — that breaks TEAM.md's explicit hour-0-3 goal ("fog_sim.py v0 ... unblocks P4
today"); if fog_sim can't run, P4 has nothing to build ingest/dedup/flusher against.

**This creates a real, dated obligation, not a someday:** P5's `auth/hashing.py` must
be real before **hour 12** — P3's seeder and any actual blacklist/tracking demo depend
on every producer (fog_sim, api, seeder) hashing with the exact same function and key.
Flagged to P5 directly; don't assume it lands in time without checking.

---

## 3. CSP hardening: nonce-based vs. targeted tightening (resolved 2026-09-12, corrected same day after production-build testing)

**Problem:** `/security-review` flagged a permissive CSP (`unsafe-inline`/`unsafe-eval`
in `script-src`) — low confidence (2/10, no currently-reachable XSS sink) but a real
hardening gap.

**Correction — read this before touching this file's original claim:** the first pass
at this decision assumed `script-src 'self'` with no `unsafe-inline` was achievable
because "Next.js's own code loads via external `<script src>` files." **This was
tested against a real production build and is false.** Next.js App Router inlines its
RSC hydration payload as `<script>(self.__next_f=...)</script>` tags on every page
(7 of them on `/login` alone) — framework-level, present in every Next 15 App Router
production build, not something our components introduced. There is no "just omit
unsafe-inline" for App Router; only a full nonce implementation (or Next's
experimental SRI feature) removes it.

**Actual resolution:**
- `script-src` keeps `'unsafe-inline'` — required for the framework to hydrate at all.
  Not a gap we chose; structurally required by App Router without a full nonce
  implementation. Documented with a code comment in `next.config.ts` so nobody
  "fixes" this again without knowing why.
- `'unsafe-eval'` is still dropped in production — unaffected by the above, real,
  zero-cost, still lands.
- `style-src` keeps `'unsafe-inline'` for the reasons already given below (inline
  `style=""` attributes aren't covered by nonces regardless of script-src).
- Since there's no currently-reachable XSS sink (per the original review), allowing
  `unsafe-inline` in `script-src` doesn't add exploitable risk on top of what already
  exists — CSP's script restriction only matters once there's an injection point to
  exploit, and there isn't one right now.

**Nonce-based CSP is now clearly the *only* way to ever remove `script-src
'unsafe-inline'` in App Router** — not just "more hardening," structurally required.
Still rejected for this hackathon timeline: it means renaming `middleware.ts` to
`proxy.ts` (reopening §1's resolved passthrough decision) and forcing every page to
dynamic rendering (losing static prerendering just verified above). Logged as the real
backlog item it now clearly is — worth real consideration post-hackathon or if the
team ever hardens this for a non-demo deployment, not something to attempt mid-build
for a currently non-exploitable gap.

---

## 4. Team-chat data shapes conflict with the frozen contract (flagged 2026-09-12; OD sub-issue resolved 2026-09-13)

**Problem:** informal notes relayed from Nawfal describe a trajectory shape
(`vehicle_id`/`trajectory[]` with `camera`/`timestamp`/`transition`) that does not
match TEAM.md §4.4's frozen shape (`plate`/`segments[]` with `camera_id`/`ts`/`type`/
`lat`/`lon`) — notably, the new shape has **no lat/lon at all**. The same notes describe
an "OD (Origin-Destination)" analytics feature, which TEAM.md §11 explicitly lists as
an **L1 non-goal** ("do NOT build" until L2/L3 stretch). A DB shape with a `Speed`
column was also mentioned, not present in TEAM.md §8's schema.

**This is not resolved — it is an open flag, not a decision.** Two real possibilities:
either the team has actually revised the frozen contract and TEAM.md itself needs a
team-visible update, or these are informal exploratory notes that haven't been agreed
as a change. Building frontend UI as if this were confirmed would repeat exactly the
kind of silent deviation TEAM.md §1 warns against.

**Working approach until confirmed:**
- New visualizations implied by these notes (per-segment congestion coloring,
  OD flow lines, a "Routes" view) are built as **prototypes behind the same
  unconfirmed-data treatment as mock mode** — real and demoable, but visibly flagged
  as not-yet-reconciled with the actual API contract, never silently presented as if
  they were the shipped shape.
- Where the new trajectory shape lacks lat/lon, the working assumption is a client-side
  join against `db/cameras.json` by camera ID — reasonable, but itself unconfirmed with
  the team, and isolated behind a swappable type/adapter so it's a small change either
  way once the real shape is confirmed.
- Industry convention for segment congestion coloring (for when this is built):
  green (low) → yellow (moderate) → orange (heavy) → red (severe) — standard across
  Mapbox Traffic, TomTom, and ArcGIS; no need to invent a different scheme.
- **Do not let this quietly become the new frozen contract.** Wahid must get an
  explicit answer from Nawfal/P4 on whether the trajectory shape and OD's in-scope
  status have actually changed, and if so, TEAM.md gets updated for the whole team —
  not just this file.

**OD sub-issue resolved 2026-09-13, authorized by Wahid.** OD is confirmed real and
in-scope — TEAM.md §11 updated to remove it from the L1 non-goal list (dated note
there, not a silent edit). It shipped as a first-class `AnalyticsViewSelector` view
(`od-flow`), not folded into the exact PS vocabulary wording (Traffic Density /
Heatmap / Corridor Speeds) — a real, flagged deviation from that CLAUDE.md/TEAM.md
wording, not a bug. Built via `components/map/ODFlowLayer.tsx` (promoted from its
former `GisPreviewPanel` prototype slot, restyled from violet to the analyst cyan
accent), `lib/mock/fixtures.ts`'s `mockOdFlows()`, and `hooks/useAnalytics.ts`'s
`useOdFlows()` — same pattern as `useDensity`/`useHeatmap`, hitting a mocked
`/analytics/od` with no real backend endpoint yet (still not in TEAM.md §4.4; confirm
field names with P4 when it lands). Segments and Routes — the other two prototypes
this section describes — remain exactly as built/labeled; this authorization was
specifically about OD, not blanket permission to de-prototype the rest. The trajectory
lat/lon-shape question this section originally raised is still open.

---

## 5. The right-edge gray region has been reported "fixed" twice and is not fixed (open 2026-09-12)

**Problem:** a gray region on the right edge of every page, asymmetric (content flush
left, gap only on the right), was flagged, "fixed" in one session with a plausible
root-cause story (AmbientBackground), and reported resolved without the numeric
`scrollWidth`/`innerWidth` proof that was explicitly required. It reappeared. A second
session skipped the required Part 0 verification entirely and jumped to feature work.
The bug is still present per a live screenshot, on both `/login` and `/analytics`.

**This is now a process problem, not just a CSS problem.** A future session must
produce the actual numeric before/after, not a narrative "checked, fine" — treat any
report of this bug being fixed without those numbers as not actually resolved.

---

**Resolved 2026-09-12 (third session) — real root cause found, not AmbientBackground.**

No `scrollWidth`/`clientWidth` mismatch was reproducible on `/login` at all — that page
already measured `scrollWidth === clientWidth === innerWidth` at 1920×1080 before any
change this session. The actual visible defect was on `/analytics`: a distinct gray
box appearing to the *left* of the `AnalyticsViewSelector` dropdown ("Traffic Density"
/ "GIS Preview (prototype)" etc.), looking like a leftover, unstyled control sitting
next to the real one.

**Root cause, identified by name:** `components/ui/native-select.tsx`'s `NativeSelect`
applied its incoming `className` prop (glass background, border, glow, rounded-xl —
everything `AnalyticsViewSelector.tsx` passes in) to the outer positioning `<div
data-slot="native-select-wrapper">` instead of to the actual `<select
data-slot="native-select">` element. The inner `<select>` kept its own hardcoded
`border border-input bg-transparent ...` classes with no way to receive an override.
Result: two visually different boxes stacked — a styled glass wrapper (`pl-8` padding
reserved for the icon) behind a plain-bordered, transparent-background `<select>` that
didn't fill it, reading as an orphaned gray control to the left of the "real" one. Not
a scroll-container or overflow bug at all — `document.documentElement.scrollWidth` was
never actually larger than `clientWidth` in this reproduction; the appearance was
purely a stacked/mismatched-background illusion from the two elements occupying
overlapping space with different paddings.

**Fix:** moved the `cn(...)` merge in `native-select.tsx` so the wrapper `<div>` keeps
only its structural classes (`group/native-select relative w-fit
has-[select:disabled]:opacity-50`) and the passed-in `className` merges onto the
`<select>` itself, alongside its base styling. Single call site affected
(`AnalyticsViewSelector.tsx`), so blast radius is one component.

**Numeric verification after the fix** (`document.documentElement.scrollWidth` /
`.clientWidth` / `window.innerWidth`, tracker role, `/analytics` and `/tracking`,
Windows/Chromium via Playwright, scrollbar reserves ~15px of `innerWidth` at some
sizes — that gap is normal OS scrollbar gutter, not overflow, confirmed by
`scrollWidth === clientWidth` in every case):

| Viewport | Page | scrollWidth | clientWidth | innerWidth |
|---|---|---|---|---|
| 1920×1080 | /analytics | 1920 | 1920 | 1920 |
| 1920×1080 | /tracking | 1905 | 1905 | 1920 |
| 1440×900 | /analytics | 1440 | 1440 | 1440 |
| 1440×900 | /tracking | 1425 | 1425 | 1440 |
| 1366×768 | /analytics | 1366 | 1366 | 1366 |
| 1366×768 | /tracking | 1351 | 1351 | 1366 |

`scrollWidth === clientWidth` at every size on both pages — no horizontal overflow.
Visual gray-box artifact confirmed gone by screenshot at all three sizes on
`/analytics` (where it was reproducible) after the `native-select.tsx` fix.

**Marking this closed.** Unlike the prior two "fixed" claims, this one names the exact
file/element, explains why the previous AmbientBackground theory was never the actual
cause, and carries the numbers above. If it reappears a fourth time, it is not this bug
— take a fresh screenshot and re-diagnose from zero rather than assuming this fix
regressed.

---

## 6. Nawfal's real analytics/cameras contract lands, supersedes part of TEAM.md §4.4 (resolved 2026-09-13)

**What changed:** P4 (Nawfal) delivered a real, non-prototype API contract for six
endpoints — `GET /cameras`, `GET /analytics/summary`, `GET /analytics/segments`,
`GET /analytics/heatmap`, `GET /analytics/od`, `GET /analytics/routes`. This
**replaces** (not adds to) `/analytics/density`, the old `[{lat,lon,weight}]`
`/analytics/heatmap` shape, and `/analytics/corridor-speeds` from TEAM.md §4.4 —
those three are gone. TEAM.md §4.4/§4.4.1 updated in the same session, struck through
rather than silently removed, per this file's own rule against silent contract drift.

Full shapes, copied verbatim from the handoff:

```
GET /cameras                 -> {cameras:[{camera_id,latitude,longitude,road_id}]}
GET /analytics/summary       -> {vehicles_analyzed, transitions_analyzed,
                                 average_speed_kmh, median_speed_kmh,
                                 average_travel_time_sec, congested_segments,
                                 total_segments}
GET /analytics/segments      -> {segments:[{from_camera,to_camera,from_road,
                                 to_road,vehicle_count,average_speed_kmh,
                                 average_travel_time_sec,congestion:"HIGH"|
                                 "MEDIUM"|"LOW"}]}
GET /analytics/heatmap       -> {points:[{camera_id,latitude,longitude,
                                 vehicle_count,average_speed_kmh}]}
GET /analytics/od            -> {flows:[{origin,destination,vehicle_count}]}
                                 origin/destination are ROAD_IDs, not coordinates
GET /analytics/routes        -> {routes:[{route_id,road_sequence:[road_id...],
                                 vehicle_count,average_speed_kmh,
                                 average_travel_time_sec}]}
```

**Real technical decision — road_id → coordinate resolution (`lib/roads.ts`):**
`/analytics/od`'s `origin`/`destination` and `/analytics/routes`' `road_sequence` are
`road_id` strings, not coordinates, and multiple cameras can share a `road_id`.
Chose to **average the lat/lon of every camera sharing a road_id** into one centroid
per road (`buildRoadCoordinateIndex()`), rather than taking the first matching camera.
Reasoning: averaging is stable regardless of `/cameras`' return order; a road_id's
"position" is inherently a same-road cluster, not one arbitrarily-chosen canonical
point. This is a judgment call, not a contract fact — flag to Nawfal/P4 if the real
backend later has an opinion on this (e.g. a road midpoint or geometry it already
computes server-side).

**GIS prototypes promoted to first-class, all three (not just Segments/OD):**
`GisPreviewPanel`, `lib/gis-prototype/*`, `types/gis-prototype.ts`, and
`PrototypeBanner` are deleted — every remaining analytics view now has a real,
contracted endpoint backing it, so the "unconfirmed prototype" treatment no longer
applies to anything. Segments and OD were explicitly named in the handoff; Routes
was promoted alongside them (Wahid's call, since `/analytics/routes` is equally real
and leaving Routes alone as the sole remaining "prototype" would have been
inconsistent — see the session's `AskUserQuestion` decision log). `SegmentsLayer` now
resolves coordinates directly off `/cameras` (camera-pair keyed, no road_id
averaging needed); `RoutesLayer`/`ODFlowLayer` use `lib/roads.ts`'s road_id
averaging.

**Congestion/role/status color tokens centralized:** `app/globals.css` now defines
`--congestion-high/medium/low`, `--role-tracker/analyst`, `--status-live/warning`
once; `lib/colors.ts` mirrors the congestion/status hexes for Mapbox paint
expressions and inline styles (which can't resolve CSS `var()`). `CONGESTION_COLORS`
no longer lives in the now-deleted `lib/gis-prototype/adapter.ts` — every component
that colors by congestion (`SegmentsLayer`, `AnalyticsViewSelector`'s legend) reads
from `lib/colors.ts` now. This was mostly already in decent shape before this
session — role/alert colors already referenced `--tracker`/`--analyst`/`--alert`
CSS tokens in `RoleBadge`, `AlertConsole`, `BlacklistPanel` — the actual gap was
congestion coloring living in the soon-to-be-deleted prototype adapter file.

## 7a. `main`'s backend is completely empty — authorized emergency backend build (2026-09-13, authorized by Wahid)

**Finding:** verifying the NaN-LngLat fix and demo readiness against a real backend
required actually starting one. `docker-compose.yml` at repo root is 0 bytes. Checked
every file P1/P3/P4/P5 own — `api/*.py` (all 9 files), `db/*.sql`/`db/cameras.json`,
`auth/*.py`, `fog-node/{enhance,ocr,fusion,pipeline}.py` — every single one is 0 bytes,
confirmed via `git show HEAD:<path> | wc -c` (not just an uncommitted local
working-tree gap): committed empty in the very first commit (`e769f12`, "File
struture") and never filled in by anyone since. `TEAM.md` documents a fully working,
locally-tested backend (checkpoints at hour 3/12/16, P3's schema applied, P4's
ingest/tracking/analytics, P5's auth/JWT) — none of that work was ever actually pushed
to `main`. The only real, non-empty files in the whole repo outside `frontend/` are
`fog-node/fog_sim.py` (P2's own file) — everything else P1/P3/P4/P5 were assigned is a
zero-byte placeholder. This is a materially bigger and more urgent problem than the
main-vs-testd divergence originally flagged this session: there was, at the time of
this check, no working backend anywhere on `main` to test the frontend against, mock
mode notwithstanding.

**Authorization:** Wahid explicitly authorized building a real backend from scratch
this session, scoped to demo-day necessity, against `TEAM.md`'s frozen contract
(§4.4/§4.4.1) — **not** a general standing license for this frontend-owning session to
keep editing `api/`/`db`/`auth/` afterward. This is a one-time, logged exception to
CLAUDE.md's ownership boundary, made explicitly and in writing, to be replaced by
P3/P4/P5's actual implementation the moment any of them push real work. Everything
under §7b below is Claude-Code-authored emergency scaffolding, not P1/P3/P4/P5's work —
do not attribute it to them, and do not treat its presence as evidence those
checkpoints were ever actually met on `main`.

## 7. Mapbox GL → MapLibre GL swap, tokenless basemap (resolved 2026-09-13, authorized by Wahid)

**Problem:** local verification of the NaN-LngLat fix (`SegmentsLayer`/`TrajectoryLayer`,
commit `9ec6b19`) needed a real, loaded map to distinguish a real regression from noise.
With `NEXT_PUBLIC_MAPBOX_TOKEN` empty (correctly — it's a real credential, never
committed), Mapbox GL never loads a style/canvas, and its own internal
`mousemove`/`mouseover` handlers throw `Invalid LngLat object: (NaN, NaN)` from
`Map.unproject()` on an uninitialized projection — a token-absence artifact that
surfaces with the exact same error string as the real bug this session was asked to
verify, with no way to tell them apart without a working map.

**A Mapbox account token cannot be created or fetched by an agent** — it's
account/billing-bound, not a lookup. Asked Wahid directly rather than guess or embed
any scraped/shared token (CLAUDE.md bans any credential in `frontend/`, and a public
demo token found via search is exactly that kind of embedded credential, plus likely
dead/rate-limited).

**Resolution, authorized live:** swap the map library from Mapbox GL JS to MapLibre GL
JS (`react-map-gl/maplibre` instead of `react-map-gl`'s default Mapbox export — same
component API, `Marker`/`Popup`/`Source`/`Layer` usage unchanged across
`SegmentsLayer`/`ODFlowLayer`/`RoutesLayer`/`HeatmapLayer`/`TrajectoryLayer`), against
CARTO's free, tokenless `dark-matter-gl-style` vector basemap
(`basemaps.cartocdn.com`) — no signup, no key, no CLAUDE.md security-rule tension.

**What changed:**
- `package.json`: `maplibre-gl` added, `mapbox-gl`/`@types/mapbox-gl` removed.
- `components/map/CityMap.tsx`: `Map` import from `react-map-gl/maplibre`, `mapStyle`
  points at the CARTO URL, `mapboxAccessToken` prop dropped entirely, CSS import
  swapped to `maplibre-gl/dist/maplibre-gl.css`.
- Five layer components: import path changed to `react-map-gl/maplibre` only —
  `Source`/`Layer`/`Marker`/`Popup` usage untouched.
- `TrajectoryLayer.tsx`'s popup class selectors: `.mapboxgl-popup-*` →
  `.maplibregl-popup-*` (MapLibre's own DOM class names).
- `next.config.ts` CSP: `style-src`/`img-src`/`connect-src` now allow
  `basemaps.cartocdn.com` instead of `api.mapbox.com`/`*.tiles.mapbox.com`.
- `.env.local`, `.env.local.example`: `NEXT_PUBLIC_MAPBOX_TOKEN` removed — no map
  token variable exists in this app anymore.
- CLAUDE.md's tech-stack line and `NEXT_PUBLIC_*` security rule updated to match —
  not a silent edit, per this file's own rule.

**Not done:** did not touch `db/`, `api/`, or `auth/`; did not evaluate MapLibre against
any other basemap provider beyond CARTO's default free style — a reasonable choice for
demo purposes, revisit if the team wants a different visual treatment.

---

## 7c. Emergency backend build — implementation + real end-to-end verification (2026-09-13)

Following #7a's authorization, wrote a real backend from scratch against TEAM.md's
frozen contract: `db/schema.sql` (added a `UNIQUE` constraint on `cameras.road_node_id`
that the original spec didn't call out — needed as an FK target for `road_edges`),
`db/cameras.json` (matches frontend's existing `MOCK_CAMERAS` exactly, so no camera_id
drift), `db/seed.py` (Python, not `.sql` — hashing must happen at insert time via
`auth/hashing.py`), `db/sweeper.py`, `auth/hashing.py` (HMAC-SHA256 + AES-GCM),
`auth/jwt.py`, and the full `api/` package (`main.py`, `deps.py`, `ingest.py`,
`tracking.py` with real A* bridging via `graph.py`, `analytics.py`'s six endpoints,
`alerts.py`, `flusher.py`, `models.py`, `schemas.py`) plus `docker-compose.yml` and
`api/Dockerfile`. Fresh secrets generated for `.env` (gitignored); `.env.example`
documents the keys with empty values.

**Real bugs caught and fixed during `docker compose up` verification, not just written
and assumed correct:**
- Schema: `road_edges` FK to `cameras.road_node_id` failed at Postgres init — no unique
  constraint existed on the referenced column. Added `UNIQUE`.
- `api/models.py`'s `get_db` vs `get_conn` — routes were wired to `Depends(get_conn)`
  (the raw `@contextmanager`, not a generator dependency), causing
  `AttributeError: '_GeneratorContextManager' object has no attribute 'cursor'` on
  every DB-touching route. Fixed by using `get_db` consistently.
- `/ingest` auth header mismatch: `fog_sim.py` (P2's own existing file) sends
  `X-Fog-Api-Key`, but the new endpoint checked `Authorization: Bearer`. Fixed to match
  fog_sim's already-established convention rather than change fog_sim.
- `/cameras` was accidentally role-gated; frontend's `lib/cameras.ts`/`hooks/useCameras.ts`
  already assumed (and states in a comment) this endpoint is unauthenticated. Removed the
  gate to match that pre-existing frontend assumption instead of relitigating it.

**Verified end-to-end for real, not just "should work":** `docker compose up` from a
clean `-v` volume state boots cleanly; `fog-node/fog_sim.py` (unmodified) ingests real
blocks that flow through Redis streams into Postgres via the flusher; a real blacklist
hit on `MH12AB1284` fires a real alert visible in the frontend's 10s-polling banner; real
`/track/.../bridged` returns real A*-bridged inferred segments between camera pairs on
different road nodes; role gating produces real 403s (tracker → `/analytics/*`, analyst →
`/track/.../bridged`) — the frontend's own login/nav/empty-state handling was exercised
against this, not simulated. `tsc --noEmit`, `eslint`, and `next build` all clean against
the real backend (`NEXT_PUBLIC_MOCK_MODE=false`).

**Security review (two independent passes) on the new backend found two real, fixed
issues:** (1) `api/main.py`'s CORS was `allow_origins=["*"]` — narrowed to a
`FRONTEND_ORIGIN` env var (default `http://localhost:3000`), methods/headers narrowed
to what's actually used. (2) Both the fog ingest key check (`api/ingest.py`) and the
demo password check (`auth/jwt.py`) used plain `!=` string comparison instead of
constant-time — swapped to `hmac.compare_digest` in both places. No SQL injection, JWT
algorithm-confusion, path traversal, or plaintext-leak-to-analyst issues found in either
pass — every `cur.execute()` call already used parameterized `%s` placeholders.

**Scope discipline:** this build is a one-time, logged exception (#7a). It has not been
committed/pushed as of this writing — pending Wahid's go-ahead per the master prompt's
Phase 8. It should be replaced by P3/P4/P5's real work the moment any of them push it;
nothing here should be read as evidence those checkpoints were actually met by the team.

---

**Vocabulary divergence from TEAM.md's original "exact PS vocabulary" instruction —
now a visible, three-sessions-deep line item, not something that quietly happened:**
`AnalyticsViewSelector` now ships six views — Traffic Density (repurposed as a
`/analytics/summary` KPI row + per-camera chart, no longer per-camera-only),
Heatmap, Corridor Speeds (redriven from `/analytics/segments`, richer than the old
per-edge node speed), OD Flow, Segments, and Busiest Routes — none of which are the
literal three-item "Traffic Density / Heatmap / Corridor Speeds" wording TEAM.md §8
and CLAUDE.md originally specified. Each individual deviation was flagged in its own
session (OD in DECISIONS.md #4; Density/Corridor Speeds' re-sourcing and
Segments/Routes' promotion in this entry) — this paragraph exists specifically so
the *cumulative* drift is visible in one place before demo day, per the master
prompt's explicit instruction not to let it quietly happen. **Not a blocker, but
worth a team gut-check before the judges see it** — the PS vocabulary requirement
may matter more to judges than the richer feature set does.

---

## 8. Real-road seed regen + `geometry` field on segments/routes/od — unfrozen by Wahid alone, explicitly NOT team consensus (2026-09-13)

**What this is:** master prompt v11 asked for `db/cameras.json` (frozen per TEAM.md
§4.3/§5) to be regenerated from real OSM road geometry (via `osmnx`/`networkx`,
offline preprocessing only, no runtime network dependency) instead of the current
procedural grid (`scripts/generate_seed.py`), and for a `geometry`
(`[[lon,lat],...]`) field to be added to `/analytics/segments`, `/analytics/routes`,
and `/analytics/od` so the frontend can draw real street-following polylines instead
of straight camera-to-camera / road-to-road connectors.

Claude Code initially refused to proceed: `cameras.json` is explicitly marked FROZEN
in TEAM.md, and `db/schema.sql` / `api/schemas.py` / `api/analytics.py` are P3/P4-owned
files under CLAUDE.md's ownership boundary. A first claim of "the team agrees" was not
verifiable against anything in this repo and was not accepted as authorization.

**Authorization, stated plainly:** Wahid is authorizing this himself, as himself, not
as team consensus. Same basis as #7a's emergency backend build — P3/P4 have not landed
real work on `main` this session, and Wahid has been making these calls out of
necessity all week. This is **not** claimed to be a P3/P4-agreed contract change; it is
a one-time, logged, single-person override of two things TEAM.md marks as frozen/
teammate-owned:

1. `db/cameras.json` — unfrozen for regeneration from real Delhi/Noida OSM road
   network data (real intersections, betweenness-centrality-biased camera placement,
   density skewed toward central Delhi vs. Noida/Ghaziabad periphery).
2. `db/schema.sql`, `api/schemas.py`, `api/analytics.py` — a `geometry` field is added
   to the `road_edges` table and threaded through to `/analytics/segments`,
   `/analytics/routes`, and `/analytics/od` responses (real OSM edge vertices for
   segments; full concatenated real-path vertices, computed via `networkx`
   shortest-path at seed time, for routes/OD). All other fields on these responses are
   unchanged from TEAM.md §4.4.1.

**What this is explicitly not:** not evidence P3/P4 reviewed or agreed to a schema
change; not a standing license for future sessions to keep editing `db/`/`api/` — same
one-time-exception framing as #7a. Should be replaced by P3/P4's real, reviewed
implementation the moment either pushes real work, exactly as #7a says for the rest of
the emergency backend.

**Reliability constraint carried over unchanged from the master prompt:** OSM/osmnx
network access happens only in the offline seed-generation script
(`scripts/generate_seed.py`), never at request time — the running app has zero runtime
dependency on OSM/Overpass availability.
