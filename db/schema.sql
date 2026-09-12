CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS cameras (
  camera_id TEXT PRIMARY KEY,
  lat DOUBLE PRECISION NOT NULL,
  lon DOUBLE PRECISION NOT NULL,
  zone TEXT NOT NULL,
  road_node_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('tracker', 'analyst'))
);

CREATE TABLE IF NOT EXISTS plates (
  plate_hash TEXT PRIMARY KEY,
  plate_text_enc TEXT NOT NULL,
  first_seen TIMESTAMPTZ NOT NULL,
  last_seen TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sightings (
  id UUID PRIMARY KEY,
  plate_hash TEXT NOT NULL REFERENCES plates(plate_hash) ON DELETE CASCADE,
  camera_id TEXT NOT NULL REFERENCES cameras(camera_id),
  ts TIMESTAMPTZ NOT NULL,
  conf DOUBLE PRECISION NOT NULL,
  outcome TEXT NOT NULL,
  alt_hashes TEXT[] NOT NULL DEFAULT '{}',
  quality TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blacklist (
  plate_hash TEXT PRIMARY KEY,
  reason TEXT NOT NULL,
  added_by TEXT NOT NULL,
  added_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alert_events (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,
  plate_hash TEXT NOT NULL,
  camera_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  detail JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  who TEXT NOT NULL,
  role TEXT NOT NULL,
  action TEXT NOT NULL,
  target_hash TEXT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS road_edges (
  from_node TEXT NOT NULL,
  to_node TEXT NOT NULL,
  length_m DOUBLE PRECISION NOT NULL,
  speed_limit_kmh DOUBLE PRECISION NOT NULL,
  typical_speeds JSONB NOT NULL,
  PRIMARY KEY (from_node, to_node)
);

CREATE INDEX IF NOT EXISTS idx_sightings_plate_ts ON sightings (plate_hash, ts);
CREATE INDEX IF NOT EXISTS idx_sightings_camera_ts ON sightings (camera_id, ts);
