import type { AlertEvent, DebugHashResponse, Trajectory } from "@/types/tracking";
import type { AnalyticsSummary, HeatmapPoint, OdFlow, Route, Segment } from "@/types/analytics";
import type { ApiCamera } from "@/types/cameras";
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

// Real contract from Nawfal (P4), 2026-09-13 — see TEAM.md §4/DECISIONS.md
// #6. Supersedes the old mockDensity/mockCorridorSpeeds/{lat,lon,weight}
// mockHeatmap/zone-centroid mockOdFlows below (removed, not kept as
// dead code — anyone building against those old shapes needs to know now).

export function mockCamerasResponse(): { cameras: ApiCamera[] } {
  return {
    cameras: MOCK_CAMERAS.map((c) => ({
      camera_id: c.camera_id,
      latitude: c.lat,
      longitude: c.lon,
      road_id: c.road_node_id,
    })),
  };
}

export function mockAnalyticsSummary(): AnalyticsSummary {
  return {
    vehicles_analyzed: 342,
    transitions_analyzed: 518,
    average_speed_kmh: 41.6,
    median_speed_kmh: 38.2,
    average_travel_time_sec: 214,
    congested_segments: 3,
    total_segments: 8,
  };
}

export function mockHeatmap(): HeatmapPoint[] {
  return MOCK_CAMERAS.map((c, i) => ({
    camera_id: c.camera_id,
    latitude: c.lat,
    longitude: c.lon,
    vehicle_count: 20 + i * 11 + (i % 2 === 0 ? 8 : 0),
    average_speed_kmh: 30 + i * 4,
  }));
}

// Segments are camera-pair keyed (from_camera/to_camera), not road-node
// edges — six adjacent camera pairs along the seeded chain.
export function mockSegments(): Segment[] {
  const pairs: [string, string, string, string, number, number, number, Segment["congestion"]][] =
    [
      ["CAM_01", "CAM_02", "N1", "N2", 18, 34, 210, "LOW"],
      ["CAM_02", "CAM_03", "N2", "N3", 52, 22, 340, "HIGH"],
      ["CAM_03", "CAM_04", "N3", "N4", 34, 41, 180, "MEDIUM"],
      ["CAM_04", "CAM_05", "N4", "N5", 81, 19, 410, "HIGH"],
      ["CAM_05", "CAM_06", "N5", "N6", 27, 47, 150, "LOW"],
      ["CAM_01", "CAM_06", "N1", "N6", 63, 27, 300, "MEDIUM"],
    ];
  return pairs.map(
    ([from_camera, to_camera, from_road, to_road, vehicle_count, average_speed_kmh, average_travel_time_sec, congestion]) => ({
      from_camera,
      to_camera,
      from_road,
      to_road,
      vehicle_count,
      average_speed_kmh,
      average_travel_time_sec,
      congestion,
      // No real OSM geometry in mock mode — SegmentsLayer falls back to a
      // straight from/to line, same as it always did before DECISIONS.md #8.
      geometry: [],
    }),
  );
}

export function mockOdFlows(): OdFlow[] {
  const roadIds = MOCK_CAMERAS.map((c) => c.road_node_id);
  const flows: [string, string, number][] = [
    [roadIds[0]!, roadIds[2]!, 84],
    [roadIds[0]!, roadIds[3]!, 47],
    [roadIds[4]!, roadIds[0]!, 62],
    [roadIds[5]!, roadIds[0]!, 29],
  ];
  return flows.map(([origin, destination, vehicle_count]) => ({
    origin,
    destination,
    vehicle_count,
    // No real OSM path in mock mode — ODFlowLayer falls back to a straight
    // origin/destination line, same as before DECISIONS.md #8.
    geometry: [],
  }));
}

export function mockRoutes(): Route[] {
  const routes: { roads: string[]; vehicle_count: number }[] = [
    { roads: ["N1", "N2", "N3"], vehicle_count: 96 },
    { roads: ["N4", "N5", "N6"], vehicle_count: 71 },
    { roads: ["N1", "N6"], vehicle_count: 63 },
  ];
  return routes
    .sort((a, b) => b.vehicle_count - a.vehicle_count)
    .map((r, i) => ({
      route_id: `route_${i + 1}`,
      road_sequence: r.roads,
      vehicle_count: r.vehicle_count,
      average_speed_kmh: 32 + i * 5,
      average_travel_time_sec: 260 - i * 30,
      // No real OSM path in mock mode — RoutesLayer falls back to
      // resolveRoadCoordinate()-based straight segments, same as before
      // DECISIONS.md #8.
      geometry: [],
    }));
}
