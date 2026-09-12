"use client";

import { Source, Layer } from "react-map-gl";
import type { OdFlowPoint } from "@/types/analytics";

interface ODFlowLayerProps {
  flows: OdFlowPoint[];
}

// Origin/destination flow lines between zone centroids, line width +
// opacity encoding vehicle_count. OD confirmed in-scope 2026-09-13,
// authorized by Wahid — supersedes the TEAM.md §11 L1 non-goal listing; see
// DECISIONS.md #4 for the full history. Promoted from the GisPreviewPanel
// prototype into a first-class AnalyticsViewSelector view (restyled to the
// analyst accent, was violet). Straight lines, not curved great-circle
// arcs — a real feature, but width/opacity encoding is intentionally simple
// pending a real /analytics/od endpoint.
export function ODFlowLayer({ flows }: ODFlowLayerProps) {
  const maxVolume = Math.max(...flows.map((f) => f.vehicle_count), 1);

  return (
    <Source
      id="analytics-od-flows"
      type="geojson"
      data={{
        type: "FeatureCollection",
        features: flows.map((f) => ({
          type: "Feature",
          properties: { vehicle_count: f.vehicle_count },
          geometry: { type: "LineString", coordinates: [f.origin, f.destination] },
        })),
      }}
    >
      <Layer
        id="analytics-od-flows-line"
        type="line"
        layout={{ "line-cap": "round" }}
        paint={{
          "line-width": [
            "interpolate",
            ["linear"],
            ["get", "vehicle_count"],
            0,
            1.5,
            maxVolume,
            10,
          ],
          "line-opacity": [
            "interpolate",
            ["linear"],
            ["get", "vehicle_count"],
            0,
            0.25,
            maxVolume,
            0.75,
          ],
          "line-color": "#38bdf8",
        }}
      />
    </Source>
  );
}
