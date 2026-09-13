-- SentinelGrid — db/schema.sql
-- Plaintext MVP version for high-speed ingestion

CREATE TABLE IF NOT EXISTS cameras (
    camera_id       TEXT PRIMARY KEY,
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    zone            TEXT NOT NULL,
    road_node_id    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    installed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS road_edges (
    from_node           TEXT NOT NULL,
    to_node             TEXT NOT NULL,
    length_m            DOUBLE PRECISION NOT NULL,
    speed_limit_kmh     DOUBLE PRECISION NOT NULL,
    typical_speeds      JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (from_node, to_node)
);

CREATE TABLE IF NOT EXISTS sightings (
    block_id        UUID PRIMARY KEY,
    plate_text      TEXT NOT NULL,
    camera_id       TEXT NOT NULL REFERENCES cameras(camera_id),
    ts              TIMESTAMPTZ NOT NULL,
    conf            DOUBLE PRECISION NOT NULL,
    outcome         TEXT NOT NULL,
    alt_texts       TEXT[] NOT NULL DEFAULT '{}',
    quality         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sightings_plate_ts  ON sightings (plate_text, ts);
CREATE INDEX IF NOT EXISTS idx_sightings_camera_ts ON sightings (camera_id, ts);

CREATE TABLE IF NOT EXISTS blacklist (
    plate_text  TEXT PRIMARY KEY,
    reason      TEXT NOT NULL,
    added_by    TEXT NOT NULL,
    added_ts    TIMESTAMPTZ NOT NULL DEFAULT now()
);



CREATE TABLE IF NOT EXISTS alert_events (
    id          BIGSERIAL PRIMARY KEY,
    type        TEXT NOT NULL,
    plate_text  TEXT NOT NULL,
    camera_id   TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    who         TEXT NOT NULL,
    role        TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_text TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);