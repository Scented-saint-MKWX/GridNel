"use client";

import { useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { OdFlow } from "@/types/analytics";
import { resolveRoadCoordinate } from "@/lib/roads";
import { FLOW_VOLUME_COLORS } from "@/lib/colors";

interface ODFlowLayerProps {
  flows: OdFlow[];
  roadCoordinateIndex: Map<string, [number, number]>;
  topN?: number;
}

// Bends a straight origin->destination line into a quadratic-ish curve by
// offsetting its midpoint perpendicular to the line, so distinct flows that
// share an origin or destination don't visually stack into one segment and
// so direction reads as a curve, not a ruler-straight connector. Real
// road-geometry paths (DECISIONS.md #8) are used as-is when available since
// they already follow the street network; this only applies to the
// straight-line fallback.
function curvedPath(origin: [number, number], destination: [number, number]): [number, number][] {
  const [x1, y1] = origin;
  const [x2, y2] = destination;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy);
  if (dist === 0) return [origin, destination];
  const bend = dist * 0.15;
  const mx = (x1 + x2) / 2 + (-dy / dist) * bend;
  const my = (y1 + y2) / 2 + (dx / dist) * bend;
  const points: [number, number][] = [];
  const steps = 16;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Quadratic Bezier through (origin, control, destination).
    const x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * mx + t ** 2 * x2;
    const y = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * my + t ** 2 * y2;
    points.push([x, y]);
  }
  return points;
}

// Builds a small filled-triangle polygon centered at `tip`, pointing along
// `bearingDeg` (compass degrees, 0 = north) — a real geometric arrowhead
// rather than a text-symbol glyph. Chosen over a `text-field` glyph
// specifically because CARTO's dark-matter style only ships glyph PBFs for
// its own named font stacks (Montserrat/Open Sans/Noto Sans/...) and
// arbitrary Unicode arrow codepoints (▲ U+25B2, ➤ U+27A4) aren't guaranteed
// present in those subset ranges — confirmed silently dropped in a real
// browser check this session, not just a theoretical risk. `sizeDegLon` is
// in the same lon/lat-degree units as the source data (small, since this
// renders at city scale) rather than pixels, so it stays proportionally
// legible as ["interpolate"] scales it with vehicle_count like every other
// OD paint property.
function arrowheadPolygon(
  tip: [number, number],
  bearingDeg: number,
  sizeDegLon: number,
): [number, number][] {
  const rad = (bearingDeg * Math.PI) / 180;
  const back = sizeDegLon * 1.6;
  const half = sizeDegLon * 0.7;
  // Local basis: forward = direction of travel, right = perpendicular.
  const fwd: [number, number] = [Math.sin(rad), Math.cos(rad)];
  const right: [number, number] = [Math.cos(rad), -Math.sin(rad)];
  const base = (t: number, s: number): [number, number] => [
    tip[0] - fwd[0] * back * t + right[0] * half * s,
    tip[1] - fwd[1] * back * t + right[1] * half * s,
  ];
  return [tip, base(1, 1), base(0.65, 0), base(1, -1), tip];
}

// Real GET /analytics/od (Nawfal, 2026-09-13, TEAM.md §4). Master prompt v12
// Phase 2: directional curved arcs (not flat lines) with an arrowhead
// showing origin->destination, width/opacity scaled continuously by
// vehicle_count, capped to the top N flows so the busiest corridors stay
// legible instead of every flow overlapping into visual noise.
export function ODFlowLayer({ flows, roadCoordinateIndex, topN = 15 }: ODFlowLayerProps) {
  const { data, arrowData, maxVolume } = useMemo(() => {
    const resolved = flows.flatMap((f) => {
      const origin = resolveRoadCoordinate(roadCoordinateIndex, f.origin);
      const destination = resolveRoadCoordinate(roadCoordinateIndex, f.destination);
      if (!origin || !destination) return [];
      return [{ ...f, origin, destination }];
    });
    const top = [...resolved].sort((a, b) => b.vehicle_count - a.vehicle_count).slice(0, topN);
    const maxVolume = Math.max(...top.map((f) => f.vehicle_count), 1);

    const withPaths = top.map((f) => ({
      ...f,
      path: (f.geometry && f.geometry.length >= 2
        ? f.geometry
        : curvedPath(f.origin, f.destination)) as [number, number][],
    }));

    const data = {
      type: "FeatureCollection" as const,
      features: withPaths.map((f) => ({
        type: "Feature" as const,
        properties: { vehicle_count: f.vehicle_count },
        geometry: { type: "LineString" as const, coordinates: f.path },
      })),
    };

    // One arrowhead polygon per flow, tip placed near the destination end
    // and rotated to face along the final path segment — real directional
    // indicator rather than an undifferentiated line. Size scales with
    // vehicle_count same as the line width/opacity (continuous encoding,
    // not a flat fixed-size marker).
    const arrowData = {
      type: "FeatureCollection" as const,
      features: withPaths.flatMap((f) => {
        const path = f.path;
        if (path.length < 2) return [];
        const idx = Math.max(1, Math.floor(path.length * 0.88));
        const a = path[idx - 1]!;
        const b = path[Math.min(idx, path.length - 1)]!;
        const bearingDeg = (Math.atan2(b[0] - a[0], b[1] - a[1]) * 180) / Math.PI;
        const t = f.vehicle_count / maxVolume;
        const size = 0.0009 + t * 0.0016;
        return [
          {
            type: "Feature" as const,
            properties: { vehicle_count: f.vehicle_count },
            geometry: {
              type: "Polygon" as const,
              coordinates: [arrowheadPolygon(b, bearingDeg, size)],
            },
          },
        ];
      }),
    };

    return { data, arrowData, maxVolume };
  }, [flows, roadCoordinateIndex, topN]);

  return (
    <>
      <Source id="analytics-od-flows" type="geojson" data={data}>
        <Layer
          id="analytics-od-flows-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            "line-width": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 1.5, maxVolume, 9],
            "line-opacity": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 0.25, maxVolume, 0.85],
            "line-color": [
              "interpolate",
              ["linear"],
              ["get", "vehicle_count"],
              0,
              FLOW_VOLUME_COLORS.low,
              maxVolume,
              FLOW_VOLUME_COLORS.high,
            ],
          }}
        />
      </Source>

      <Source id="analytics-od-arrows" type="geojson" data={arrowData}>
        <Layer
          id="analytics-od-arrows-layer"
          type="fill"
          paint={{
            "fill-color": [
              "interpolate",
              ["linear"],
              ["get", "vehicle_count"],
              0,
              FLOW_VOLUME_COLORS.low,
              maxVolume,
              FLOW_VOLUME_COLORS.high,
            ],
            "fill-opacity": 0.95,
          }}
        />
      </Source>
    </>
  );
}
