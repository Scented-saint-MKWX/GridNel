INSERT INTO cameras (camera_id, lat, lon, zone, road_node_id) VALUES
('CAM_01', 28.6139, 77.2090, 'central', 'N1'),
('CAM_02', 28.6181, 77.2138, 'central', 'N2'),
('CAM_03', 28.6222, 77.2204, 'central', 'N3'),
('CAM_04', 28.6054, 77.2299, 'east', 'N4'),
('CAM_05', 28.5995, 77.2180, 'east', 'N5'),
('CAM_06', 28.6073, 77.2008, 'east', 'N6')
ON CONFLICT (camera_id) DO NOTHING;

INSERT INTO road_edges (from_node, to_node, length_m, speed_limit_kmh, typical_speeds) VALUES
('N1','N2',1100,50,'{"0":35,"6":32,"9":28,"12":26,"18":24,"22":30}'),
('N2','N1',1100,50,'{"0":35,"6":32,"9":28,"12":26,"18":24,"22":30}'),
('N2','N3',980,45,'{"0":34,"6":30,"9":26,"12":24,"18":22,"22":28}'),
('N3','N2',980,45,'{"0":34,"6":30,"9":26,"12":24,"18":22,"22":28}'),
('N3','N4',1800,55,'{"0":42,"6":38,"9":32,"12":30,"18":26,"22":35}'),
('N4','N3',1800,55,'{"0":42,"6":38,"9":32,"12":30,"18":26,"22":35}'),
('N4','N5',1200,45,'{"0":30,"6":28,"9":22,"12":20,"18":18,"22":26}'),
('N5','N4',1200,45,'{"0":30,"6":28,"9":22,"12":20,"18":18,"22":26}'),
('N5','N6',2100,60,'{"0":46,"6":42,"9":36,"12":34,"18":30,"22":38}'),
('N6','N5',2100,60,'{"0":46,"6":42,"9":36,"12":34,"18":30,"22":38}'),
('N1','N6',1600,50,'{"0":36,"6":34,"9":29,"12":27,"18":25,"22":31}'),
('N6','N1',1600,50,'{"0":36,"6":34,"9":29,"12":27,"18":25,"22":31}')
ON CONFLICT (from_node, to_node) DO NOTHING;

-- Demo-only seeded credentials; pbkdf2 hashes for tracker/track123 and analyst/analytics123.
INSERT INTO users (username, password_hash, role) VALUES
('tracker', 'pbkdf2$120000$795a842b7aeb884de47a9d2952c85b97$0e6fa6d69edf808fede54f7beda73e8a61721beec529f182b05e8c0490f3a9bf', 'tracker'),
('analyst', 'pbkdf2$120000$6fe6a182f363a8dae31cf798ea2c40cb$97616ae34f7969097e3522ecfc47a5adefa8816a562a26bca587c29c228d9669', 'analyst')
ON CONFLICT (username) DO NOTHING;

-- HMAC-SHA256 in SQL with env HMAC_KEY (base64); mirrors auth/hashing.py logic for seed data.
INSERT INTO blacklist (plate_hash, reason, added_by)
VALUES (
  encode(hmac('MH12AB1284', decode(current_setting('app.hmac_key', true), 'base64'), 'sha256'),'hex'),
  'stolen_vehicle_demo',
  'seed'
)
ON CONFLICT (plate_hash) DO NOTHING;
