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
