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
