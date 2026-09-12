# SentinelGrid — Team Build Guide (PS 127)

*Rule:* this document is the single source of truth. If anything conflicts with something someone remembers, *this file wins*. Propose changes in the group chat; never silently deviate.

---

## 1. What we are building (30-second version)

SentinelGrid turns a city's *existing, siloed ANPR cameras* into a unified platform that can (a) reconstruct any vehicle's route across the city, (b) compute city-wide traffic analytics, and (c) fire real-time alerts — *without replacing any camera, sending video centrally, or storing identifiable data beyond a short TTL window.*

Our five demo beats, mapped to the PS text:
1. Live ingestion from mock fog nodes → "centralized platform, multi-camera feeds"
2. *Blacklist alert fires live* → "Alert System … in real time"
3. Vehicle tracking with a blind spot bridged on the map → "Single Plate Trajectory Tracking"
4. Analytics dashboard (density + heatmap + corridor speeds) → "Macro Traffic Flow Analytics"
5. TTL deletion + audit log shown → privacy architecture made visible

---

## 2. Team and ownership

| Who | Owns | Backup duty |
|---|---|---|
| *P1 — CV / Fog pipeline* | fog-node/: enhance, OCR, fusion, pipeline, validation dataset | accuracy slide |
| *P2 — Frontend + Demo* | frontend/ (Next.js + Mapbox), fog_sim.py, scripts/replay.py, *demo script* | helps P1 with dataset |
| *P3 — Database* | db/: schema, seeds, sweeper, analytics SQL | helps P4 with flusher SQL |
| *P4 — Server computation* | api/: ingest, flusher, tracking + A* bridging, analytics, alerts | helps P5 with compose |
| *P5 — Security + DevOps* | auth/ (HMAC/AES/JWT/middleware), docker-compose.yml, .env policy, audit log | integration firefighter |

*P2 is demo owner.* After hour 26, the demo script outranks every feature.

---

## 3. Architecture (everyone must be able to draw this from memory)

```
ANPR Camera ──event {vendor_guess, JPEG crop}──▶ FOG NODE (one per camera cluster; cameras NOT modified)
                                                   1. enhance crop (grayscale → 2-3x upscale → CLAHE)
                                                   2. OCR (PaddleOCR, swappable block)
                                                   3. FUSE vendor_guess vs engine_read
                                                   4. RESOLVE conflict → one plate per event
                                                   5. HMAC-SHA256 → build DATA BLOCK
                                                   6. POST /ingest  (crop never stored, never forwarded)
                                                           │
                                                           ▼
                                                 CENTRAL: FastAPI + Redis
                                                   validate → fog auth → dedupe (5s, SETNX)
                                                   → blacklist check (ALERT PATH, never skipped)
                                                   → Redis stream ──flusher──▶ PostgreSQL (TTL sweeper)
                                                           │
                                                           ▼
                                                 ENGINES (read-only):
                                                   Tracking (privileged) + A* blind-spot bridging + misread self-heal
                                                   Analytics (unprivileged): density / heatmap / corridor speeds
                                                   Alerts: blacklist hits + impossible-speed anomaly
                                                           │
                                                           ▼
                                                 FRONTEND: Tracking | Analytics | Alert console
```

*Four rules that never change:*
1. Video/JPEG never leaves the fog node (RAM only, processed, discarded).
2. Everything downstream of the fog consumes *only the data block*.
3. Analytics can never see plaintext — only the tracking endpoint can decrypt.
4. One ingestion path serves all camera tiers: Tier A (event+crop), Tier B (text only), Tier C (RTSP → same OCR code on sampled frames). L1 demo uses Tier A semantics.

---

## 4. Frozen contracts (agreed hour 0–3; DO NOT change after hour 3)

### 4.1 The Data Block (fog → api)

```json
{
  "block_id": "uuid4",
  "camera_id": "CAM_01",
  "cam_event_id": "evt_88d2",
  "ts": "2026-09-12T03:41:07+05:30",
  "plate_hash": "a9f3c1...",
  "plate_text_enc": "AES-GCM ciphertext b64",
  "conf": 0.93,
  "location": { "lat": 28.6139, "lon": 77.2090 },
  "resolution": {
    "fused_as": "MH12AB1284",
    "outcome": "agreement",
    "vendor_guess": "MH12AB1234",
    "alt_hashes": ["b27d..."]
  },
  "quality": "full_pipeline"
}
```

- outcome ∈ agreement | engine_preferred | vendor_preferred | single_channel | low_confidence
- quality ∈ full_pipeline | anpr_fallback | unverified
- alt_hashes = HMAC hashes of *rejected* candidate reads (may be [], never plaintext)
- vendor_guess optional but always include when available — the fusion demo moment depends on it

### 4.2 Environment variables (P5 owns .env, gitignored; .env.example committed empty)

```
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
REDIS_URL=redis://redis:6379/0
HMAC_KEY            # 32+ bytes b64 — fog-node AND api (via shared auth/hashing.py)
AES_KEY             # 32 bytes b64 — api only (tracking decryption)
JWT_SECRET          # api only
FOG_API_KEY         # fog → api credential
RETENTION_HOURS=24
```

No key ever in source code. Fog and api import the *same* hashing.py — one import, one behavior.

### 4.3 Shared seed: db/cameras.json (read by DB seeder, fog_sim, frontend — nobody hardcodes cameras)

Six cameras across two zones, each with camera_id, lat, lon, zone, road_node_id (N1–N6). P4 additionally seeds road_edges(from_node, to_node, length_m, speed_limit_kmh, typical_speeds) connecting N1→N6 with realistic distances — A* bridging and speed checks depend on it.

### 4.4 API surface (frozen shapes)

```
POST /ingest                     fog only, FOG_API_KEY
GET  /healthz
POST /login                       {username, password} → JWT {sub, role}
GET  /alerts?since=...            both roles; L1 = polling (NO WebSocket)
GET  /track/<plate_text>          tracker only; server hashes plaintext; chronological trajectory
GET  /track/<plate_text>/bridged  tracker only; + A*-inferred gap segments
POST /blacklist                   tracker only {plate_text, reason}
DELETE /blacklist/<plate_hash>    tracker only
GET  /analytics/density?hours=1   analyst; per-camera counts
GET  /analytics/heatmap?hours=1   analyst; [{lat, lon, weight}]
GET  /analytics/corridor-speeds   analyst; per-edge avg implied speed
GET  /debug/hash/<text>           tracker only; demo helper so frontend can link search text → hash
```

Trajectory response:
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

Analyst-role responses get plate_text_enc stripped by middleware (P5) — P4 returns it in the shape; middleware enforces removal.

---

## 5. Repo layout (monorepo, one repo)

```
sentinelgrid/
├── docker-compose.yml          P5
├── .env.example                P5
├── TEAM.md
├── db/
│   ├── cameras.json            FROZEN hour 3
│   ├── schema.sql               P3
│   ├── seed.sql                 P3 (cameras, road_edges, ONE blacklisted plate)
│   └── sweeper.py               P3 — TTL deletion
├── api/
│   ├── main.py                  P4 — app factory + routers
│   ├── models.py                P4 (P3 reviews)
│   ├── schemas.py               P4 — Pydantic block contract (4.1)
│   ├── ingest.py                P4 — /ingest + dedupe + blacklist check
│   ├── flusher.py               P4 — Redis stream → batch Postgres insert
│   ├── tracking.py              P4 — /track + impossible-speed + self-heal
│   ├── graph.py                 P4 — road graph + A* (~60 lines, pure Python)
│   ├── analytics.py             P4 — density / heatmap / corridor-speeds
│   └── alerts.py                P4 — /alerts read
├── auth/
│   ├── hashing.py                P5 — hmac_plate / encrypt_plate / decrypt_plate
│   └── jwt.py                    P5 — issue/verify, roles
├── fog-node/
│   ├── enhance.py                P1
│   ├── ocr.py                    P1 — BaseOCR → PaddleOCRImpl (swappable)
│   ├── fusion.py                 P1 — Section 6 rules
│   ├── pipeline.py               P1 — enhance→ocr→fusion→block
│   ├── images/                   P1 — validation crops (gitignored)
│   └── fog_sim.py                P2 — mock camera (mode A instant mock / mode B real pipeline)
├── frontend/                     P2 — Next.js: /login /tracking /analytics + alert console
└── scripts/replay.py             P2 — re-drives recorded events through /ingest
```

Branches: main protected; personal branches; PR merges at the three checkpoints; after hour 16 direct commits to main for bugfixes only.

---

## 6. Fusion / conflict-resolution rules (P1 implements, P4 stores, everyone understands)

| # | Situation | Rule | outcome |
|---|---|---|---|
| 1 | Identical, conf ≥ 0.85 | Emit; conf = max | agreement |
| 2 | Differ by 1 char, engine conf > vendor | Engine wins; vendor variant → alt_hashes | engine_preferred |
| 3 | Differ by 1 char, vendor conf > engine | Vendor wins; engine variant → alt_hashes | vendor_preferred |
| 4 | Differ by ≥ 2 chars | Emit only if best conf ≥ 0.90, else *DROP* | low_confidence |
| 5 | One channel only | Emit if conf ≥ 0.85, else drop | single_channel |
| 6 | Same hash + camera within 5s | Dedupe at API (SETNX 5s TTL), keep first | discarded |

Principle: *a garbage block is worse than no block* — a wrong plate silently splits trajectories.

---

## 7. Hour-by-hour plan

### Hour 0–3 — Contracts + skeletons (EVERYONE)
- [ ] Everyone reads this file; resolve ambiguity in chat now.
- [ ] P3: cameras.json + road_edges proposal → group approves → *frozen*.
- [ ] P5: .env.example, docker-compose.yml skeleton with healthchecks and depends_on: condition: service_healthy. Deadline: this phase.
- [ ] P4+P3: schema.sql + Pydantic schemas.py against 4.1.
- [ ] P1+P2: fog_sim.py v0 emitting fabricated blocks straight from 4.1 (no OCR yet) — unblocks P4 today.
- [ ] P2: Next.js boots; routes stubbed.

*Checkpoint 1 (hour 3):* mock block flows sim → api stub → 200. Contracts frozen forever.

### Hour 3–12 — Vertical slice
- [ ] P4: /ingest complete (validate → SETNX dedupe → blacklist check → Redis stream sightings:stream).
- [ ] P4: flusher.py (consumer group; batch 200 rows or 3s; upsert plates.first_seen/last_seen; XACK after commit). *Hour-12 blocker — without it the DB stays empty and nothing demos.*
- [ ] P3: schema applied in compose Postgres; seeder loads cameras + road_edges + one blacklisted plate (seed hashes plaintext via auth/hashing.py).
- [ ] P3: sweeper.py (every 5 min: delete expired sightings; delete plates with no sightings and stale last_seen).
- [ ] P5: POST /login (demo users tracker/track123, analyst/analytics123); role middleware stripping plate_text_enc for analysts; audit_log writes on every /track*.
- [ ] P2: Mapbox map with camera markers from cameras.json; /track polyline rendering against fake data.
- [ ] P1: offline dataset — 100–200 labeled plate crops, ~20% deliberately degraded (blur/rotate/darken).

*Checkpoint 2 (hour 12):* a mock block ingested by the REAL stack appears on the REAL map. From here the project cannot die.

### Hour 12–16 — Parallel depth
- [ ] P1: enhance + OCR on dataset; *measured accuracy number* (expect 80–95%; slide shows number + failure gallery + swap-ready design).
- [ ] P4: /track real query; impossible-speed anomaly → alert_events; analytics endpoints.
- [ ] P3: analytics SQL verified on seeded data.
- [ ] P5: blacklist add/delete (tracker-only); FOG_API_KEY enforcement; /debug/hash gated.
- [ ] P2: analytics page (dropdown → chart + heatmap layer); alert console (10s polling).

*Checkpoint 3 (hour 16):* docker compose up on a fresh machine gives the full system. Everyone demos from compose after this.

### Hour 16–26 — Demo features
- [ ] P4: *A bridging** in graph.py — validated gaps filled over road_edges (weight = length / typical_speed[hour]); /track/<text>/bridged returns observed + inferred segments.
- [ ] P4: *self-healing v1* — on an impossible-speed leg, query sightings matching endpoint blocks' alt_hashes; if a variant forms a plausible continuation, stitch it ("healed": true).
- [ ] P1: wire real pipeline into fog_sim.py mode B (real crops → real blocks). Keep mode A as fallback.
- [ ] P2: replay.py records a good run and re-drives it in identical order/timing. *The demo runs on replay.*
- [ ] P2+P1: sim injections — p=0.05 blacklisted plate; p≈0.10 vendor_guess one-char misread (exercises engine_preferred + fusion display); p≈0.05 low_confidence drop.
- [ ] P5: audit-log viewer endpoint (tracker-only); TTL/audit demo queries prepared.

### Hour 26–31 — Freeze + rehearsal
- [ ] Feature freeze at hour 26. No new endpoints, no refactors.
- [ ] P2: demo script finalized; rehearsed end-to-end twice.
- [ ] P4: replay guaranteed to contain a blacklist hit at minute 2 and a bridgeable gap at minute 3.
- [ ] P5: fresh-clone test on a teammate's machine: git clone && cp .env.example .env && docker compose up works.
- [ ] P1: accuracy slide final.

### Hour 31–36 — Buffer / stretch (only if rehearsed twice)
Stretch order: WebSocket alerts → OD matrix → PostGIS column → live-mode flourish. If behind: cut analytics to density+heatmap, cut bridging to one hardcoded gap — *never cut the five demo beats.*

---

## 8. Per-person specs ("done" definitions)

### P1 — CV / Fog pipeline
Done = pipeline.py(image, vendor_guess) → (plate, conf, alt_hashes) + measured accuracy report.
- Enhancement fixed order: grayscale → Lanczos 2–3× → CLAHE → optional denoise (low-quality crops only). ~15 lines, worth 5–10 points — don't skip.
- OCR behind BaseOCR interface — judges hear "any model drops in."
- Fusion = Section 6 exactly; alt_hashes populated on rules 2/3 (P4's self-heal depends on it).
- Validation: label 100–200 crops (filename = ground truth), report character-level accuracy.
- Running pipeline never writes crops to disk; dataset folder is dev-only, gitignored.

### P2 — Frontend + Demo
Done = two modes + alert console + replay, all against compose APIs, rehearsed demo script.
- Login: role picker → /login → JWT (memory preferred, localStorage acceptable demo).
- Tracking: plaintext input → /track/<text>/bridged → *solid* polyline observed, *dashed* inferred; camera markers with ts + outcome on click; healed segments get a "self-corrected misread" badge.
- Analytics: dropdown in PS vocabulary (Traffic Density / Heatmap / Corridor Speeds), analyst role; heatmap = Mapbox heat layer.
- Alerts: 10s polling; blacklist hit → red banner + camera flash.
- fog_sim.py: mode A instant mock (hour 3 unblock); mode B real pipeline (hour 16+); injections per Section 7.
- Demo runs on replay; live mode is the flourish.

### P3 — Database
Done = schema applied, seeded, swept, analytics queries verified.
- Tables: cameras; plates(plate_hash PK, plate_text_enc, first_seen, last_seen); sightings(id, plate_hash FK, camera_id FK, ts, conf, outcome, alt_hashes text[], quality); blacklist(plate_hash PK, reason, added_by, added_ts); alert_events(id, type, plate_hash, camera_id, ts, detail jsonb); audit_log(who, role, action, target_hash, ts); road_edges(...).
- Indexes: sightings(plate_hash, ts) and sightings(camera_id, ts). Nothing else at L1.
- One unified sightings table — *no per-plate tables*; per-plate history is WHERE plate_hash=X ORDER BY ts.
- Sweeper every 5 min; log one line per run.
- Seed includes exactly one blacklisted plate — e.g. MH12AB1284; tell P2 and P4.

### P4 — Server computation
Done = all 4.4 endpoints working against compose, with flusher + bridging + alerts.
- /ingest: validate → SETNX dedup:{camera}:{hash} TTL 5s → SISMEMBER blacklist → on hit write alert_events + return {"alert": true} → XADD sightings:stream. *Never INSERT to Postgres here.*
- flusher.py: consumer group; batch 200 rows or 3s; ON CONFLICT upsert plates; XACK after commit; restart-safe.
- /track: server-side HMAC via auth/hashing.py → sightings⋈cameras ordered → per-leg check: implied speed > 130 km/h = suspicious *identity*, not driving → self-heal via alt_hashes → write audit_log.
- /bridged: validated gaps → A* over road_edges (weight = length / typical_speed[hour]) → inferred segment algorithm: "astar_speed_prior".
- Analytics: density (count by camera × hour-bucket); heatmap (camera lat/lon × counts); corridor-speeds (per-plate consecutive Δt ÷ edge length, averaged per edge, excluding >130 km/h legs as misreads).
- Analysts never get plaintext — coordinate exact stripping point with P5 (they own middleware; you own queries).

### P5 — Security + DevOps
Done = one-command compose, keys never in code, two roles enforced, audit live.
- auth/hashing.py: hmac_plate(text), encrypt_plate(text) → b64, decrypt_plate(b64) → text. Keys from env. Imported by api, fog-node, and seeder.
- JWT: POST /login → {sub, role, exp}. Middleware: analysts → /track* and blacklist mutations = 403, plate_text_enc stripped. Every /track* → audit_log(who, ts, plate_hash).
- Compose: api(8000), db(5432, pg_isready healthcheck), redis(6379, redis-cli ping), frontend(3000), fog-sim (no port). depends_on: condition: service_healthy. Named pgdata volume.
- Fresh-clone test at hour 28 is your gate.
- TLS: documented as deployment step (Caddy/nginx sidecar); dev HTTP inside compose is fine — say so proactively in Q&A.

---

## 9. Privacy one-liner (everyone memorizes)

> "Identities are HMAC-hashed at the fog with a server-held key; plaintext exists only AES-encrypted and is decryptable solely by the privileged tracking service; images are processed in RAM and never stored; every sighting auto-deletes after the retention window; and every privileged lookup is audit-logged. The system cannot leak what it does not retain."

Five mechanisms: *HMAC · AES role-gating · transient images · TTL · audit.*

## 10. Numbers for Q&A

- Fog: 1 node / 16–32 Tier-A cameras; ₹30–60k; ≈₹2–4k/camera vs ₹1.5–4 lakh for a new smart-pole camera.
- Payload ≈ 500 bytes/block vs ~4 Mbps video stream (~100,000× less bandwidth).
- Storage: a year of sightings ≈ GBs vs petabytes of NVR video.
- Dedup and blacklist checks are O(1); flusher batches 200 rows per round-trip.
- Retention: 24h demo; production suggestion 30–90 days per policy.

## 11. L1 non-goals (L2/L3 — do NOT build)

HMM inference · bottleneck scoring · WebSocket push · PostGIS geometry · K8s · multi-city federation · key rotation · on-camera ACAP · runtime load-shedding. *Plain SHA-256 anywhere is formally banned* (rainbow-table reversible) — HMAC or nothing.

**2026-09-13: OD (Origin-Destination) matrix confirmed in-scope, authorized by Wahid — supersedes its prior listing here as an L1 non-goal.** See DECISIONS.md #4 for the full history and CLAUDE.md for the frontend view it now ships as.

If ahead after two rehearsals, pick from this list top-down.

## 12. Failure playbook (3 AM edition)

| Symptom | First check |
|---|---|
| Map empty | flusher running? XRANGE sightings:stream - + non-empty? seeder ran? |
| Alerts silent | blacklist seeded with hash of the right plaintext? sim injecting p=0.05? |
| Partial trajectory | 130 km/h threshold too tight? fusion populating alt_hashes? |
| api crashloops | healthchecks/depends_on conditions; missing env var vs .env.example |
| Works only on my machine | fresh-clone test failed — fix compose, never manual installs |

*Blocked > 30 minutes → post in chat with what you tried.* No silent hero debugging.

## 13. Demo script (P2 owns; rehearsed twice by hour 31)

1. (30s) Fresh docker compose up on screen.
2. (60s) Live mode: sim streams blocks; counters move.
3. (30s) *Blacklist beat:* red banner + camera flash. (Replay has the hit at minute 2; fallback = trigger via sim manually.)
4. (90s) *Tracking beat:* search MH12AB1284 → route with one *dashed A-bridged** gap + one healed segment.
5. (60s) *Analytics beat:* logout/login as analyst (privilege separation visible) → density + heatmap + speeds.
6. (45s) *Privacy beat:* run sweeper / show audit log + expired rows gone.
7. (45s) Close: accuracy slide + L2/L3 roadmap.

Fallback order: replay → screen recording → narrated slides. *Never debug on stage.*

## 14. Using copilot-prompts.md

Module-by-module, in Section 7's order — never "generate the whole repo." Every generated file is reviewed against contracts 4.1–4.4 before merge; output that deviates is wrong even if elegant. Copilot types; the group decides.

## 15. Project definition of done

- [ ] Five beats run end-to-end from fresh clone via docker compose up
- [ ] TTL sweeper demonstrably deletes; audit log demonstrably records
- [ ] Analyst token → /track returns 403 (provable live)
- [ ] Accuracy slide shows a real measured number
- [ ] Demo rehearsed twice; everyone knows which beat they narrate
- [ ] README: architecture diagram, setup, demo credentials

*Build L1 exactly as scoped. Let the roadmap do the talking.*
