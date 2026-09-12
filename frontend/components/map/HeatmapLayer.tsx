"use client";

import { Source, Layer } from "react-map-gl";
import type { HeatmapPoint } from "@/types/analytics";

interface HeatmapLayerProps {
  points: HeatmapPoint[];
}

// Mapbox heat layer per FRONTEND_BLUEPRINT.md §5 — not a chart-library heatmap.
export function HeatmapLayer({ points }: HeatmapLayerProps) {
  return (
    <Source
      id="density-heatmap"
      type="geojson"
      data={{
        type: "FeatureCollection",
        features: points.map((p) => ({
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
            "rgba(245,158,11,0.9)",
          ],
          "heatmap-radius": 25,
        }}
      />
    </Source>
  );
}
