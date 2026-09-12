"use client";

import { Source, Layer } from "react-map-gl";
import type { HeatmapPoint } from "@/types/analytics";

interface HeatmapLayerProps {
  points: HeatmapPoint[];
}

// Mapbox heat layer per FRONTEND_BLUEPRINT.md §5 — not a chart-library heatmap.
export function HeatmapLayer({ points }: HeatmapLayerProps) {
  // Guards against a backend returning malformed lat/lon (missing/null) —
  // an invalid coordinate reaching Mapbox as NaN throws and takes the map
  // down. Pure frontend robustness, not an API contract change.
  const validPoints = points.filter(
    (p) => Number.isFinite(p.lon) && Number.isFinite(p.lat),
  );

  return (
    <Source
      id="density-heatmap"
      type="geojson"
      data={{
        type: "FeatureCollection",
        features: validPoints.map((p) => ({
          type: "Feature",
          properties: { weight: p.weight },
          geometry: { type: "Point", coordinates: [p.lon, p.lat] },
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
