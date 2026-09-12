"use client";

import { useState } from "react";
import { Marker, Popup, Source, Layer } from "react-map-gl";
import { Sparkles } from "lucide-react";
import type { ObservedSegment, Trajectory } from "@/types/tracking";

interface TrajectoryLayerProps {
  trajectory: Trajectory;
}

// Solid = observed, dashed = inferred (A*-bridged) — verbatim requirement,
// TEAM.md §8 / FRONTEND_BLUEPRINT.md §5. Observed points are clickable markers
// showing ts + outcome; healed:true segments get a visible badge, not just an
// identical dot, per FRONTEND_BLUEPRINT.md §5's explicit "don't let it render
// identically to a normal segment" requirement.
export function TrajectoryLayer({ trajectory }: TrajectoryLayerProps) {
  const [selected, setSelected] = useState<ObservedSegment | null>(null);

  const observed = trajectory.segments.filter(
    (s): s is ObservedSegment => s.type === "observed",
  );
  const observedCoords: [number, number][] = observed.map((s) => [s.lon, s.lat]);
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
          layout={{ "line-cap": "round", "line-join": "round" }}
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
            layout={{ "line-cap": "round", "line-join": "round" }}
            paint={{ "line-color": "#a78bfa", "line-width": 2, "line-dasharray": [2, 2] }}
          />
        </Source>
      ))}

      {observed.map((segment, i) => (
        <Marker
          key={`${segment.camera_id}-${i}`}
          longitude={segment.lon}
          latitude={segment.lat}
          onClick={(e) => {
            e.originalEvent.stopPropagation();
            setSelected(segment);
          }}
        >
          <button
            type="button"
            className={`relative flex size-3.5 items-center justify-center rounded-full ring-2 transition-transform hover:scale-125 ${
              segment.healed
                ? "bg-healed ring-healed/40"
                : "bg-tracker ring-tracker/40"
            }`}
            aria-label={`${segment.camera_id} at ${segment.ts}`}
          >
            {segment.healed && (
              <Sparkles className="absolute -top-4 size-3 text-healed" />
            )}
          </button>
        </Marker>
      ))}

      {selected && (
        <Popup
          longitude={selected.lon}
          latitude={selected.lat}
          onClose={() => setSelected(null)}
          closeButton
          anchor="bottom"
          className="[&_.mapboxgl-popup-content]:!bg-surface-raised [&_.mapboxgl-popup-content]:!rounded-lg [&_.mapboxgl-popup-content]:!border [&_.mapboxgl-popup-content]:!border-white/10 [&_.mapboxgl-popup-content]:!p-3 [&_.mapboxgl-popup-tip]:!border-t-surface-raised"
        >
          <div className="space-y-1 text-xs">
            <div className="data-mono font-semibold text-foreground">{selected.camera_id}</div>
            <div className="data-mono text-muted-foreground">{selected.ts}</div>
            {selected.outcome && (
              <div className="text-muted-foreground">
                outcome: <span className="data-mono text-foreground">{selected.outcome}</span>
              </div>
            )}
            {selected.healed && (
              <div className="mt-1.5 inline-flex items-center gap-1 rounded-md bg-healed/15 px-1.5 py-0.5 text-healed">
                <Sparkles className="size-3" />
                self-corrected misread
              </div>
            )}
          </div>
        </Popup>
      )}
    </>
  );
}
