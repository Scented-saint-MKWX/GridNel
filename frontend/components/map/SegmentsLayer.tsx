"use client";

import { useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { Segment } from "@/types/analytics";
import type { ApiCamera } from "@/types/cameras";
import { CONGESTION_GRADIENT_STOPS } from "@/lib/colors";

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

// Congestion arrives from the API as a flat HIGH/MEDIUM/LOW bucket (no
// speed-limit ratio is exposed to the frontend), so a straight 3-color match
// makes every HIGH segment look identically "maxed out" even when their
// actual vehicle_count varies widely — that's the "uniformly alarming"
// symptom Phase 3.1 flags. Continuous fix: anchor each bucket to a base
// point on the gradient (LOW->0.2, MEDIUM->0.5, HIGH->0.8) and nudge within
// the bucket by the segment's own vehicle_count relative to the dataset's
// max, so two HIGH segments with very different volumes still read
// differently. This is a frontend-only presentation smoothing, not a claim
// about the real underlying speed ratio api/analytics.py computed — see
// PR notes for the separate finding that fog_sim's congestion assignment
// may be too uniform across segments to begin with.
const BUCKET_BASE: Record<string, number> = { LOW: 0.15, MEDIUM: 0.5, HIGH: 0.82 };
const BUCKET_SPAN = 0.15;

export function SegmentsLayer({ segments, cameras }: SegmentsLayerProps) {
  const data = useMemo(() => {
    const cameraById = new Map(cameras.map((c) => [c.camera_id, c]));
    const maxCount = Math.max(...segments.map((s) => s.vehicle_count), 1);

    const features = segments.flatMap((s) => {
      const from = cameraById.get(s.from_camera);
      const to = cameraById.get(s.to_camera);
      if (!isFiniteCamera(from) || !isFiniteCamera(to)) return [];
      // Real OSM edge vertices when available (DECISIONS.md #8) — falls
      // back to the straight from/to line for any segment predating the
      // geometry field or missing a direct road_edges row.
      const coordinates =
        s.geometry && s.geometry.length >= 2
          ? s.geometry
          : [
              [from.longitude, from.latitude],
              [to.longitude, to.latitude],
            ];
      const base = BUCKET_BASE[s.congestion] ?? BUCKET_BASE.LOW!;
      const within = s.vehicle_count / maxCount; // 0..1
      const load = Math.min(1, Math.max(0, base + (within - 0.5) * BUCKET_SPAN));
      return [
        {
          type: "Feature" as const,
          properties: { congestion: s.congestion, vehicle_count: s.vehicle_count, load },
          geometry: {
            type: "LineString" as const,
            coordinates,
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
            "interpolate",
            ["linear"],
            ["get", "load"],
            ...CONGESTION_GRADIENT_STOPS.flat(),
          ],
          "line-opacity": 0.85,
        }}
      />
    </Source>
  );
}
