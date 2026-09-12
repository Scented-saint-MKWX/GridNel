import type { AlertEvent, DebugHashResponse, Trajectory } from "@/types/tracking";
import type { CorridorSpeed, DensityPoint, HeatmapPoint } from "@/types/analytics";
import type { JwtPayload, Role } from "@/types/auth";

// Fixtures mirror the frozen contract shapes byte-for-byte (TEAM.md §4.4) —
// the point is to pixel-perfect the UI against real shapes, never a shape we
// made up. Do not add/rename/remove fields here without updating TEAM.md first.

const BLACKLISTED_PLATE = "MH12AB1284";

export const MOCK_CAMERAS = [
  { camera_id: "CAM_01", lat: 28.6139, lon: 77.209, zone: "central", road_node_id: "N1" },
  { camera_id: "CAM_02", lat: 28.6229, lon: 77.2185, zone: "central", road_node_id: "N2" },
  { camera_id: "CAM_03", lat: 28.6304, lon: 77.2177, zone: "north", road_node_id: "N3" },
  { camera_id: "CAM_04", lat: 28.6089, lon: 77.2295, zone: "east", road_node_id: "N4" },
  { camera_id: "CAM_05", lat: 28.5994, lon: 77.2081, zone: "south", road_node_id: "N5" },
  { camera_id: "CAM_06", lat: 28.6167, lon: 77.1962, zone: "west", road_node_id: "N6" },
];

function makeJwt(payload: JwtPayload): string {
  const header = { alg: "none", typ: "JWT" };
  const b64 = (obj: unknown) => btoa(JSON.stringify(obj)).replace(/=+$/, "");
  return `${b64(header)}.${b64(payload)}.mocksig`;
}

export function mockLogin(role: Role): { token: string } {
  const payload: JwtPayload = {
    sub: role === "tracker" ? "tracker" : "analyst",
    role,
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  };
  return { token: makeJwt(payload) };
}

// One dashed inferred segment (CAM_02 -> CAM_03, a genuine blind-spot gap)
// plus one healed:true segment, per the master prompt's mock-fixture spec.
export function mockTrajectory(plate: string): Trajectory {
  return {
    plate,
    segments: [
      {
        type: "observed",
        camera_id: "CAM_01",
        ts: "2026-09-12T03:41:07+05:30",
        lat: 28.6139,
        lon: 77.209,
        outcome: "agreement",
      },
      {
        type: "observed",
        camera_id: "CAM_02",
        ts: "2026-09-12T03:43:52+05:30",
        lat: 28.6229,
        lon: 77.2185,
        outcome: "engine_preferred",
      },
      {
        type: "inferred",
        from: "CAM_02",
        to: "CAM_03",
        ts_start: "2026-09-12T03:43:52+05:30",
        ts_end: "2026-09-12T03:47:18+05:30",
        path: [
          [77.2185, 28.6229],
          [77.222, 28.6265],
          [77.2199, 28.6304],
          [77.2177, 28.6304],
        ],
        algorithm: "astar_speed_prior",
      },
      {
        type: "observed",
        camera_id: "CAM_03",
        ts: "2026-09-12T03:47:18+05:30",
        lat: 28.6304,
        lon: 77.2177,
        outcome: "vendor_preferred",
        healed: true,
      },
    ],
  };
}

export function mockDebugHash(plateText: string): DebugHashResponse {
  return { plate_text: plateText, plate_hash: `unhashed::${plateText}` };
}

let alertSeq = 0;
export function mockAlerts(since: string): AlertEvent[] {
  // Emit a fresh blacklist alert only once per mount cycle so the console
  // demonstrates the beat without spamming every 10s poll.
  if (alertSeq > 0) return [];
  alertSeq += 1;
  const now = new Date().toISOString();
  if (since >= now) return [];
  return [
    {
      id: `evt_${Date.now()}`,
      type: "blacklist_hit",
      plate_hash: `unhashed::${BLACKLISTED_PLATE}`,
      camera_id: "CAM_04",
      ts: now,
      detail: { plate: BLACKLISTED_PLATE, reason: "stolen vehicle report" },
    },
  ];
}

export function mockDensity(): DensityPoint[] {
  return MOCK_CAMERAS.map((c, i) => ({
    camera_id: c.camera_id,
    hour: "2026-09-12T03:00:00+05:30",
    count: 12 + i * 7 + (i % 2 === 0 ? 5 : 0),
  }));
}

export function mockHeatmap(): HeatmapPoint[] {
  return MOCK_CAMERAS.flatMap((c) => [
    { lat: c.lat, lon: c.lon, weight: Math.round(20 + Math.random() * 60) },
    {
      lat: c.lat + (Math.random() - 0.5) * 0.01,
      lon: c.lon + (Math.random() - 0.5) * 0.01,
      weight: Math.round(10 + Math.random() * 30),
    },
  ]);
}

export function mockCorridorSpeeds(): CorridorSpeed[] {
  const edges: [string, string][] = [
    ["N1", "N2"],
    ["N2", "N3"],
    ["N3", "N4"],
    ["N4", "N5"],
    ["N5", "N6"],
  ];
  return edges.map(([from_node, to_node], i) => ({
    from_node,
    to_node,
    avg_speed_kmh: 28 + i * 6,
  }));
}
