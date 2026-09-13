-- Emergency backend build, 2026-09-13 — see DECISIONS.md #7a. Reconstructed
-- from TEAM.md §8 (P3 spec) since the real schema.sql was never committed.
-- One unified sightings table; per-plate history is WHERE plate_hash=X ORDER BY ts.

CREATE TABLE IF NOT EXISTS cameras (
    camera_id     TEXT PRIMARY KEY,
    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL,
    zone          TEXT,
    road_node_id  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS road_edges (
    from_node        TEXT NOT NULL REFERENCES cameras(road_node_id),
    to_node          TEXT NOT NULL REFERENCES cameras(road_node_id),
    length_m         DOUBLE PRECISION NOT NULL,
    speed_limit_kmh  DOUBLE PRECISION NOT NULL,
    typical_speeds   JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (from_node, to_node)
);

CREATE TABLE IF NOT EXISTS plates (
    plate_hash     TEXT PRIMARY KEY,
    plate_text_enc TEXT NOT NULL,
    first_seen     TIMESTAMPTZ NOT NULL,
    last_seen      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sightings (
    id         BIGSERIAL PRIMARY KEY,
    plate_hash TEXT NOT NULL REFERENCES plates(plate_hash),
    camera_id  TEXT NOT NULL REFERENCES cameras(camera_id),
    ts         TIMESTAMPTZ NOT NULL,
    conf       DOUBLE PRECISION NOT NULL,
    outcome    TEXT NOT NULL,
    alt_hashes TEXT[] NOT NULL DEFAULT '{}',
    quality    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sightings_plate_ts ON sightings (plate_hash, ts);
CREATE INDEX IF NOT EXISTS idx_sightings_camera_ts ON sightings (camera_id, ts);

CREATE TABLE IF NOT EXISTS blacklist (
    plate_hash TEXT PRIMARY KEY,
    reason     TEXT NOT NULL,
    added_by   TEXT NOT NULL,
    added_ts   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alert_events (
    id         BIGSERIAL PRIMARY KEY,
    type       TEXT NOT NULL,
    plate_hash TEXT NOT NULL,
    camera_id  TEXT NOT NULL,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    detail     JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    who         TEXT NOT NULL,
    role        TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_hash TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);
