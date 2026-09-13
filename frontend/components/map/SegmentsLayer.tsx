"use client";

import { useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { Segment } from "@/types/analytics";
import type { ApiCamera } from "@/types/cameras";
import { CONGESTION_COLORS } from "@/lib/colors";

interface SegmentsLayerProps {
  segments: Segment[];
  cameras: ApiCamera[];
}

// Real GET /analytics/segments (Nawfal, 2026-09-13, TEAM.md §4) — promoted
// out of prototype status (was the mock-only GisPreviewPanel segments view,
// DECISIONS.md #4/#6). Segments are keyed by from_camera/to_camera, so this
// resolves coordinates directly off /cameras rather than through
// lib/roads.ts's road_id averaging (that's only needed for OD/Routes, which
// are keyed by road_id).
// Guards against a well-formed camera record with bad numbers (missing/null
// lat/lon) — same NaN-reaches-Mapbox failure mode as TrajectoryLayer /
// HeatmapLayer / CityMap, but this call site was checking only that from/to
// existed, not that their coordinates were finite.
function isFiniteCamera(c: ApiCamera | undefined): c is ApiCamera {
  return !!c && Number.isFinite(c.longitude) && Number.isFinite(c.latitude);
}

export function SegmentsLayer({ segments, cameras }: SegmentsLayerProps) {
  const data = useMemo(() => {
    const cameraById = new Map(cameras.map((c) => [c.camera_id, c]));

    const features = segments.flatMap((s) => {
      const from = cameraById.get(s.from_camera);
      const to = cameraById.get(s.to_camera);
      if (!isFiniteCamera(from) || !isFiniteCamera(to)) return [];
      return [
        {
          type: "Feature" as const,
          properties: { congestion: s.congestion, vehicle_count: s.vehicle_count },
          geometry: {
            type: "LineString" as const,
            coordinates: [
              [from.longitude, from.latitude],
              [to.longitude, to.latitude],
            ],
          },
        },
      ];
    });

    return { type: "FeatureCollection" as const, features };
  }, [segments, cameras]);

  return (
    <Source id="analytics-segments" type="geojson" data={data}>
      <Layer
        id="analytics-segments-line"
        type="line"
        layout={{ "line-cap": "round", "line-join": "round" }}
        paint={{
          "line-width": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 3, 100, 8],
          "line-color": [
            "match",
            ["get", "congestion"],
            "LOW",
            CONGESTION_COLORS.LOW,
            "MEDIUM",
            CONGESTION_COLORS.MEDIUM,
            "HIGH",
            CONGESTION_COLORS.HIGH,
            CONGESTION_COLORS.LOW,
          ],
          "line-opacity": 0.85,
        }}
      />
    </Source>
  );
}
