# SentinelGrid — Team Build Guide (PS 127)

**Rule:** this document is the single source of truth. If anything conflicts with something someone remembers, **this file wins**. Propose changes in the group chat; never silently deviate.

---

## 1. What we are building (30-second version)

SentinelGrid turns a city's **existing, siloed ANPR cameras** into a unified platform that can (a) reconstruct any vehicle's route across the city, (b) compute city-wide traffic analytics, and (c) fire real-time alerts — **without replacing any camera, sending video centrally, or storing identifiable data beyond a short TTL window.**

Our five demo beats, mapped to the PS text:
1. Live ingestion from mock fog nodes → "centralized platform, multi-camera feeds"
2. **Blacklist alert fires live** → "Alert System … in real time"
3. Vehicle tracking with a blind spot bridged on the map → "Single Plate Trajectory Tracking"
4. Analytics dashboard (density + heatmap + corridor speeds) → "Macro Traffic Flow Analytics"
5. TTL deletion + audit log shown → privacy architecture made visible

---

## 2. Team and ownership

| Who | Owns | Backup duty |
|---|---|---|
| **P1 — CV / Fog pipeline** | `fog-node/`: enhance, OCR, fusion, pipeline, validation dataset | accuracy slide |
| **P2 — Frontend + Demo** | `frontend/` (Next.js + Mapbox), `fog_sim.py`, `scripts/replay.py`, **demo script** | helps P1 with dataset |
| **P3 — Database** | `db/`: schema, seeds, sweeper, analytics SQL | helps P4 with flusher SQL |
| **P4 — Server computation** | `api/`: ingest, flusher, tracking + A* bridging, analytics, alerts | helps P5 with compose |
| **P5 — Security + DevOps** | `auth/` (HMAC/AES/JWT/middleware), `docker-compose.yml`, `.env` policy, audit log | integration firefighter |

**P2 is demo owner.** After hour 26, the demo script outranks every feature.

---

## 3. Architecture (everyone must be able to draw this from memory)

```text
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