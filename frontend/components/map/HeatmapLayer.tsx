"use client";

import { Source, Layer } from "react-map-gl";
import type { HeatmapPoint } from "@/types/analytics";

interface HeatmapLayerProps {
  points: HeatmapPoint[];
}

// Real GET /analytics/heatmap (Nawfal, 2026-09-13, TEAM.md §4) — shape is now
// {camera_id, latitude, longitude, vehicle_count, average_speed_kmh} per
// point, not the old {lat, lon, weight}. vehicle_count drives heat weight.
export function HeatmapLayer({ points }: HeatmapLayerProps) {
  // Guards against a backend returning malformed lat/lon (missing/null) —
  // an invalid coordinate reaching Mapbox as NaN throws and takes the map
  // down. Pure frontend robustness, not an API contract change.
  const validPoints = points.filter(
    (p) => Number.isFinite(p.longitude) && Number.isFinite(p.latitude),
  );

  return (
    <Source
      id="density-heatmap"
      type="geojson"
      data={{
        type: "FeatureCollection",
        features: validPoints.map((p) => ({
          type: "Feature",
          properties: { weight: p.vehicle_count },
          geometry: { type: "Point", coordinates: [p.longitude, p.latitude] },
        })),
      }}
    >
      <Layer
        id="density-heatmap-layer"
        type="heatmap"
        paint={{
          "heatmap-weight": ["get", "weight"],
          "heatmap-intensity": 1,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(56,189,248,0)",
            0.5,
            "rgba(56,189,248,0.6)",
            1,
            "rgba(217, 126, 44,0.9)",
          ],
          "heatmap-radius": 25,
        }}
      />
    </Source>
  );
}
