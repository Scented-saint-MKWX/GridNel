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
