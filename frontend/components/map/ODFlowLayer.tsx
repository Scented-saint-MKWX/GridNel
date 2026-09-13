"use client";

import { useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { OdFlow } from "@/types/analytics";
import { resolveRoadCoordinate } from "@/lib/roads";

interface ODFlowLayerProps {
  flows: OdFlow[];
  roadCoordinateIndex: Map<string, [number, number]>;
}

// Real GET /analytics/od (Nawfal, 2026-09-13, TEAM.md §4) — first-class since
// 2026-09-13 (DECISIONS.md #4), now backed by a real endpoint instead of a
// mock-only fixture. origin/destination are road_ids, resolved to
// coordinates via lib/roads.ts's per-road centroid (DECISIONS.md #6).
export function ODFlowLayer({ flows, roadCoordinateIndex }: ODFlowLayerProps) {
  const { data, maxVolume } = useMemo(() => {
    const resolved = flows.flatMap((f) => {
      const origin = resolveRoadCoordinate(roadCoordinateIndex, f.origin);
      const destination = resolveRoadCoordinate(roadCoordinateIndex, f.destination);
      if (!origin || !destination) return [];
      return [{ ...f, origin, destination }];
    });
    const maxVolume = Math.max(...resolved.map((f) => f.vehicle_count), 1);
    const data = {
      type: "FeatureCollection" as const,
      features: resolved.map((f) => ({
        type: "Feature" as const,
        properties: { vehicle_count: f.vehicle_count },
        geometry: {
          type: "LineString" as const,
          // Real shortest-path vertices when available (DECISIONS.md #8) —
          // falls back to the straight origin/destination line otherwise.
          coordinates: f.geometry && f.geometry.length >= 2 ? f.geometry : [f.origin, f.destination],
        },
      })),
    };
    return { data, maxVolume };
  }, [flows, roadCoordinateIndex]);

  return (
    <Source id="analytics-od-flows" type="geojson" data={data}>
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
