"use client";

import { useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { Route } from "@/types/analytics";
import { resolveRoadCoordinate } from "@/lib/roads";

interface RoutesLayerProps {
  routes: Route[];
  roadCoordinateIndex: Map<string, [number, number]>;
}

const RANK_COLORS = ["#d97e2c", "#38bdf8", "#a78bfa", "#94a3b8"];

// Real GET /analytics/routes (Nawfal, 2026-09-13, TEAM.md §4) — promoted out
// of prototype status. road_sequence is road_ids, resolved to coordinates via
// lib/roads.ts's averaged-per-road centroid (see DECISIONS.md #6 for the
// assumption). Ranked by vehicle_count, same rank-color/width treatment as
// the prior prototype.
export function RoutesLayer({ routes, roadCoordinateIndex }: RoutesLayerProps) {
  const { maxCount, linesData, labelsData } = useMemo(() => {
    const ranked = [...routes].sort((a, b) => b.vehicle_count - a.vehicle_count);
    const maxCount = Math.max(...ranked.map((r) => r.vehicle_count), 1);

    const withPaths = ranked.map((r, i) => ({
      ...r,
      rank: i + 1,
      // Real concatenated path vertices when available (DECISIONS.md #8) —
      // falls back to per-road-id centroid resolution for routes predating
      // the geometry field or missing a direct road_edges hop somewhere
      // along the sequence.
      path:
        r.geometry && r.geometry.length >= 2
          ? r.geometry
          : r.road_sequence
              .map((roadId) => resolveRoadCoordinate(roadCoordinateIndex, roadId))
              .filter((p): p is [number, number] => p !== null),
    }));

    const linesData = {
      type: "FeatureCollection" as const,
      features: withPaths
        .filter((r) => r.path.length >= 2)
        .map((r) => ({
          type: "Feature" as const,
          properties: { route_id: r.route_id, rank: r.rank, vehicle_count: r.vehicle_count },
          geometry: { type: "LineString" as const, coordinates: r.path },
        })),
    };

    const labelsData = {
      type: "FeatureCollection" as const,
      features: withPaths.flatMap((r) => {
        const mid = r.path[Math.floor(r.path.length / 2)];
        if (!mid) return [];
        return [
          {
            type: "Feature" as const,
            properties: { label: `#${r.rank}`, rank: r.rank },
            geometry: { type: "Point" as const, coordinates: mid },
          },
        ];
      }),
    };

    return { withPaths, maxCount, linesData, labelsData };
  }, [routes, roadCoordinateIndex]);

  return (
    <>
      <Source id="analytics-routes" type="geojson" data={linesData}>
        <Layer
          id="analytics-routes-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            "line-width": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 2, maxCount, 9],
            "line-color": [
              "match",
              ["get", "rank"],
              1,
              RANK_COLORS[0]!,
              2,
              RANK_COLORS[1]!,
              3,
              RANK_COLORS[2]!,
              RANK_COLORS[3]!,
            ],
            "line-opacity": 0.9,
          }}
        />
      </Source>

      <Source id="analytics-routes-labels" type="geojson" data={labelsData}>
        <Layer
          id="analytics-routes-label-layer"
          type="symbol"
          layout={{ "text-field": ["get", "label"], "text-size": 11, "text-offset": [0, -1] }}
          paint={{
            "text-color": [
              "match",
              ["get", "rank"],
              1,
              RANK_COLORS[0]!,
              2,
              RANK_COLORS[1]!,
              3,
              RANK_COLORS[2]!,
              RANK_COLORS[3]!,
            ],
            "text-halo-color": "#0a0e14",
            "text-halo-width": 1.5,
          }}
        />
      </Source>
    </>
  );
}
