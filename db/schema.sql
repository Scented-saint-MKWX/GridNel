-- SentinelGrid — db/schema.sql
-- Owner: P3 (Database). Applied automatically by docker-compose on Postgres startup.
-- Frozen per TEAM.md Section 8 — do not add extra tables/columns without group agreement.

-- ============================================================
-- cameras: master list of ANPR camera nodes (loaded from cameras.json)
-- ============================================================
CREATE TABLE IF NOT EXISTS cameras (
    camera_id       TEXT PRIMARY KEY,
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    zone            TEXT NOT NULL,
    road_node_id    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',   -- active | inactive
    installed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- road_edges: fixed road graph used by A* bridging (api/graph.py)
-- ============================================================
CREATE TABLE IF NOT EXISTS road_edges (
    from_node           TEXT NOT NULL,
    to_node             TEXT NOT NULL,
    length_m            DOUBLE PRECISION NOT NULL,
    speed_limit_kmh     DOUBLE PRECISION NOT NULL,
    typical_speeds      JSONB NOT NULL DEFAULT '{}'::jsonb,  -- { "0": 40, "1": 38, ... } per hour-bucket
    PRIMARY KEY (from_node, to_node)
);

-- ============================================================
-- plates: one row per unique plate_hash ever seen (rolling first/last seen)
-- ============================================================
CREATE TABLE IF NOT EXISTS plates (
    plate_hash      TEXT PRIMARY KEY,       -- HMAC-SHA256(plate_text) — never plaintext
    plate_text_enc  TEXT,                   -- AES-GCM ciphertext, b64 — decryptable only by tracking service
    first_seen      TIMESTAMPTZ NOT NULL,
    last_seen       TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- sightings: ONE unified table for every camera detection event.
-- No per-plate tables — per-plate history is `WHERE plate_hash = X ORDER BY ts`.
-- ============================================================
CREATE TABLE IF NOT EXISTS sightings (
    id              BIGSERIAL PRIMARY KEY,
    plate_hash      TEXT NOT NULL REFERENCES plates(plate_hash) ON DELETE CASCADE,
    camera_id       TEXT NOT NULL REFERENCES cameras(camera_id),
    ts              TIMESTAMPTZ NOT NULL,
    conf            DOUBLE PRECISION NOT NULL,
    outcome         TEXT NOT NULL,          -- agreement | engine_preferred | vendor_preferred | single_channel | low_confidence
    alt_hashes      TEXT[] NOT NULL DEFAULT '{}',
    quality         TEXT NOT NULL           -- full_pipeline | anpr_fallback | unverified
);

-- Required indexes (TEAM.md Section 8 — nothing else at L1)
CREATE INDEX IF NOT EXISTS idx_sightings_plate_ts  ON sightings (plate_hash, ts);
CREATE INDEX IF NOT EXISTS idx_sightings_camera_ts ON sightings (camera_id, ts);

-- ============================================================
-- blacklist: flagged vehicles
-- ============================================================
CREATE TABLE IF NOT EXISTS blacklist (
    plate_hash  TEXT PRIMARY KEY,
    reason      TEXT NOT NULL,
    added_by    TEXT NOT NULL,
    added_ts    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- alert_events: blacklist hits + anomaly flags (written instantly by api/ingest.py)
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_events (
    id          BIGSERIAL PRIMARY KEY,
    type        TEXT NOT NULL,          -- blacklist_match | anomaly
    plate_hash  TEXT NOT NULL,
    camera_id   TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- ============================================================
-- audit_log: every privileged lookup (tracking) is recorded here
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    who         TEXT NOT NULL,
    role        TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_hash TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);
