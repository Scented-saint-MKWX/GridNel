"use client";

import { Source, Layer } from "react-map-gl";
import type { Trajectory } from "@/types/tracking";

interface TrajectoryLayerProps {
  trajectory: Trajectory;
}

// Solid = observed, dashed = inferred (A*-bridged) — verbatim requirement,
// TEAM.md §8 / FRONTEND_BLUEPRINT.md §5. Healed-segment badge is a separate,
// map-marker-level concern rendered by the caller, not this layer.
export function TrajectoryLayer({ trajectory }: TrajectoryLayerProps) {
  const observedCoords: [number, number][] = trajectory.segments
    .filter((s) => s.type === "observed")
    .map((s) => [s.lon, s.lat]);

  const inferredSegments = trajectory.segments.filter((s) => s.type === "inferred");

  return (
    <>
      <Source
        id="trajectory-observed"
        type="geojson"
        data={{
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: observedCoords },
        }}
      >
        <Layer
          id="trajectory-observed-line"
          type="line"
          paint={{ "line-color": "#f59e0b", "line-width": 3 }}
        />
      </Source>
      {inferredSegments.map((segment, i) => (
        <Source
          key={`${segment.from}-${segment.to}-${i}`}
          id={`trajectory-inferred-${i}`}
          type="geojson"
          data={{
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: segment.path },
          }}
        >
          <Layer
            id={`trajectory-inferred-line-${i}`}
            type="line"
            paint={{ "line-color": "#a78bfa", "line-width": 2, "line-dasharray": [2, 2] }}
          />
        </Source>
      ))}
    </>
  );
}
