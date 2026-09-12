// Density/corridor-speed field names are inferred from TEAM.md §4.4's prose
// description ("per-camera counts", "per-edge avg implied speed"), not a verbatim
// frozen JSON shape like the trajectory response. Confirm exact field names with
// P4 when /analytics/* is live; heatmap's [{lat,lon,weight}] shape IS verbatim.
export interface DensityPoint {
  camera_id: string;
  hour: string;
  count: number;
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  weight: number;
}

export interface CorridorSpeed {
  from_node: string;
  to_node: string;
  avg_speed_kmh: number;
}

// OD (Origin-Destination) analytics — confirmed in-scope 2026-09-13,
// authorized by Wahid; supersedes the TEAM.md §11 L1 non-goal listing. See
// DECISIONS.md #4 for the full history (previously an unconfirmed prototype
// behind GisPreviewPanel; now a first-class analytics view). Shape matches
// the master prompt's spec: zone-centroid flow volumes, not a frozen TEAM.md
// §4.4 contract field (no real /analytics/od endpoint exists yet) — confirm
// exact field names with P4 when it's wired.
export interface OdFlowPoint {
  origin: [number, number]; // [lon, lat] zone centroid
  destination: [number, number]; // [lon, lat] zone centroid
  vehicle_count: number;
}
