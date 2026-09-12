"use client";

import { Source, Layer } from "react-map-gl";
import type { RoadSegment } from "@/types/gis-prototype";
import { CONGESTION_COLORS } from "@/lib/gis-prototype/adapter";

interface SegmentsLayerProps {
  segments: RoadSegment[];
}

// GIS prototype (DECISIONS.md #4) — colors road segments by congestion using
// a Mapbox data-driven line-color expression (a real GIS technique, not
// per-feature manual styling), per the master prompt's explicit requirement.
// green (low) -> yellow (moderate) -> orange (heavy) -> red (severe), the
// TomTom/Mapbox Traffic/ArcGIS industry convention already logged there.
export function SegmentsLayer({ segments }: SegmentsLayerProps) {
  return (
    <Source
      id="gis-proto-segments"
      type="geojson"
      data={{
        type: "FeatureCollection",
        features: segments.map((s) => ({
          type: "Feature",
          properties: { congestion: s.congestion, vehicle_count: s.vehicle_count },
          geometry: { type: "LineString", coordinates: [s.from, s.to] },
        })),
      }}
    >
      <Layer
        id="gis-proto-segments-line"
        type="line"
        layout={{ "line-cap": "round", "line-join": "round" }}
        paint={{
          "line-width": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 3, 100, 8],
          "line-color": [
            "match",
            ["get", "congestion"],
            "low",
            CONGESTION_COLORS.low,
            "moderate",
            CONGESTION_COLORS.moderate,
            "heavy",
            CONGESTION_COLORS.heavy,
            "severe",
            CONGESTION_COLORS.severe,
            CONGESTION_COLORS.low,
          ],
          "line-opacity": 0.85,
        }}
      />
    </Source>
  );
}
