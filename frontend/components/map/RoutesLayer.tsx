"use client";

import { Source, Layer } from "react-map-gl";
import type { RouteSummary } from "@/types/gis-prototype";

interface RoutesLayerProps {
  routes: RouteSummary[];
}

const RANK_COLORS = ["#d97e2c", "#38bdf8", "#a78bfa", "#94a3b8"];

// GIS prototype (DECISIONS.md #4) — visually distinguishes the busiest routes
// by vehicle count. Rank 1 (busiest) renders thickest/brightest; width scales
// with volume via a data-driven expression, same technique as SegmentsLayer.
export function RoutesLayer({ routes }: RoutesLayerProps) {
  const maxCount = Math.max(...routes.map((r) => r.vehicle_count), 1);

  return (
    <>
      <Source
        id="gis-proto-routes"
        type="geojson"
        data={{
          type: "FeatureCollection",
          features: routes.map((r) => ({
            type: "Feature",
            properties: { route_id: r.route_id, rank: r.rank, vehicle_count: r.vehicle_count },
            geometry: { type: "LineString", coordinates: r.path },
          })),
        }}
      >
        <Layer
          id="gis-proto-routes-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            "line-width": [
              "interpolate",
              ["linear"],
              ["get", "vehicle_count"],
              0,
              2,
              maxCount,
              9,
            ],
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

      <Source
        id="gis-proto-routes-labels"
        type="geojson"
        data={{
          type: "FeatureCollection",
          features: routes.flatMap((r) => {
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
        }}
      >
        <Layer
          id="gis-proto-routes-label-layer"
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
