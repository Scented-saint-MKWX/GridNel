-- SentinelGrid — db/seed.sql
-- Owner: P3 (Database). Run after schema.sql on a fresh database.
-- Cameras below mirror db/cameras.json exactly — keep both in sync if changed.

-- ============================================================
-- cameras
-- ============================================================
INSERT INTO cameras (camera_id, lat, lon, zone, road_node_id) VALUES
    ('CAM_01', 28.6139, 77.2090, 'Z1', 'N1'),
    ('CAM_02', 28.6162, 77.2167, 'Z1', 'N2'),
    ('CAM_03', 28.6185, 77.2245, 'Z1', 'N3'),
    ('CAM_04', 28.6220, 77.2310, 'Z2', 'N4'),
    ('CAM_05', 28.6255, 77.2380, 'Z2', 'N5'),
    ('CAM_06', 28.6290, 77.2450, 'Z2', 'N6')
ON CONFLICT (camera_id) DO NOTHING;

-- ============================================================
-- road_edges — simple chain N1-N2-N3-N4-N5-N6, bidirectional.
-- length_m estimated from cameras.json lat/lon (haversine, rounded).
-- typical_speeds keyed by hour-of-day (0-23); only a few sample hours seeded,
-- api/graph.py should default to speed_limit_kmh for any hour not listed.
-- ============================================================
INSERT INTO road_edges (from_node, to_node, length_m, speed_limit_kmh, typical_speeds) VALUES
    ('N1', 'N2', 800,  50, '{"0": 48, "8": 30, "13": 40, "18": 25, "22": 45}'),
    ('N2', 'N1', 800,  50, '{"0": 48, "8": 30, "13": 40, "18": 25, "22": 45}'),

    ('N2', 'N3', 850,  50, '{"0": 47, "8": 28, "13": 38, "18": 22, "22": 44}'),
    ('N3', 'N2', 850,  50, '{"0": 47, "8": 28, "13": 38, "18": 22, "22": 44}'),

    ('N3', 'N4', 750,  60, '{"0": 55, "8": 35, "13": 45, "18": 28, "22": 52}'),
    ('N4', 'N3', 750,  60, '{"0": 55, "8": 35, "13": 45, "18": 28, "22": 52}'),

    ('N4', 'N5', 800,  60, '{"0": 55, "8": 33, "13": 44, "18": 26, "22": 50}'),
    ('N5', 'N4', 800,  60, '{"0": 55, "8": 33, "13": 44, "18": 26, "22": 50}'),

    ('N5', 'N6', 800,  60, '{"0": 55, "8": 34, "13": 44, "18": 27, "22": 50}'),
    ('N6', 'N5', 800,  60, '{"0": 55, "8": 34, "13": 44, "18": 27, "22": 50}')
ON CONFLICT (from_node, to_node) DO NOTHING;

-- ============================================================
-- blacklist — exactly ONE seeded plate, per TEAM.md Section 8 (P3 spec).
-- Plate: MH12AB1284
--
-- *** TODO (BLOCKING) ***
-- The value below is a PLACEHOLDER, not a real HMAC hash. It must be replaced
-- with the real output of:
--     auth.hashing.hmac_plate("MH12AB1284")
-- once auth/hashing.py exists and HMAC_KEY is set in .env.
-- Do NOT demo/test blacklist-hit behavior until this placeholder is replaced —
-- ingest.py's SISMEMBER check will never match a placeholder string.
-- ============================================================
INSERT INTO plates (plate_hash, plate_text_enc, first_seen, last_seen) VALUES
    ('TODO_REPLACE_WITH_REAL_HMAC_HASH_OF_MH12AB1284', NULL, now(), now())
ON CONFLICT (plate_hash) DO NOTHING;

INSERT INTO blacklist (plate_hash, reason, added_by, added_ts) VALUES
    ('TODO_REPLACE_WITH_REAL_HMAC_HASH_OF_MH12AB1284', 'Demo: reported stolen vehicle', 'seed_script', now())
ON CONFLICT (plate_hash) DO NOTHING;
