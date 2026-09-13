// Real contract from Nawfal (P4), 2026-09-13 — see TEAM.md §4 and
// DECISIONS.md #6. Supersedes the old /analytics/density and
// /analytics/corridor-speeds shapes (per-camera counts, {lat,lon,weight}
// heatmap points, per-edge node speeds) — those are gone, do not resurrect
// them. Field names below are copied verbatim from the handoff.

export interface AnalyticsSummary {
  vehicles_analyzed: number;
  transitions_analyzed: number;
  average_speed_kmh: number;
  median_speed_kmh: number;
  average_travel_time_sec: number;
  congested_segments: number;
  total_segments: number;
}

export type CongestionLevel = "HIGH" | "MEDIUM" | "LOW";

export interface Segment {
  from_camera: string;
  to_camera: string;
  from_road: string;
  to_road: string;
  vehicle_count: number;
  average_speed_kmh: number;
  average_travel_time_sec: number;
  congestion: CongestionLevel;
  // Real OSM edge vertices [[lon,lat],...], added 2026-09-13 — DECISIONS.md
  // #8 (Wahid's one-time, logged, non-team-consensus schema exception, not
  // a P3/P4-reviewed contract change). Empty array if unavailable — layers
  // fall back to a straight from/to line.
  geometry: [number, number][];
}

export interface HeatmapPoint {
  camera_id: string;
  latitude: number;
  longitude: number;
  vehicle_count: number;
  average_speed_kmh: number;
}

// origin/destination are ROAD_IDs, not coordinates — resolved to map
// coordinates via lib/roads.ts's resolveRoadCoordinate(). See DECISIONS.md #6
// for the averaging-multiple-cameras-per-road assumption.
export interface OdFlow {
  origin: string;
  destination: string;
  vehicle_count: number;
  // Real shortest-path vertices between origin/destination, DECISIONS.md
  // #8. Empty when no direct road_edges hop exists — layer falls back to
  // resolveRoadCoordinate()'s straight line.
  geometry: [number, number][];
}

export interface Route {
  route_id: string;
  road_sequence: string[];
  vehicle_count: number;
  average_speed_kmh: number;
  average_travel_time_sec: number;
  // Full concatenated real path vertices across every hop, DECISIONS.md #8.
  // Empty when any hop lacks a direct road_edges row — layer falls back to
  // resolveRoadCoordinate()-based straight segments.
  geometry: [number, number][];
}
