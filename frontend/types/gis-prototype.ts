// GIS prototype types — NOT part of the frozen contract (TEAM.md §4). These
// back the Part 2 "GIS feature expansion" prototypes (segment congestion,
// busiest routes) flagged in DECISIONS.md #4 as built against an
// UNCONFIRMED data shape relayed informally from Nawfal, not TEAM.md §4.4.
// Never treat these as stable — see lib/gis-prototype/adapter.ts for the
// join logic that will need to change once the real shape is confirmed.
// OD flow was promoted out of this prototype set on 2026-09-13 — see
// types/analytics.ts's OdFlowPoint and DECISIONS.md #4.

export type CongestionLevel = "low" | "moderate" | "heavy" | "severe";

export interface RoadSegment {
  from_node: string;
  to_node: string;
  from: [number, number]; // [lon, lat]
  to: [number, number]; // [lon, lat]
  congestion: CongestionLevel;
  vehicle_count: number;
}

export interface RouteSummary {
  route_id: string;
  node_path: string[];
  path: [number, number][]; // [lon, lat][]
  vehicle_count: number;
  rank: number;
}
