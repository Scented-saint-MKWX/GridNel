"use client";

import { useEffect, useMemo, useState } from "react";
import { Marker, Popup, Source, Layer } from "react-map-gl";
import { Sparkles } from "lucide-react";
import type { ObservedSegment, Trajectory } from "@/types/tracking";

interface TrajectoryLayerProps {
  trajectory: Trajectory;
}

// Interpolates points along a polyline so the observed route can draw in
// over time instead of snapping in fully-formed — the "trajectory line
// drawing in" motion moment CLAUDE.md's design bar calls for explicitly.
function sliceLine(coords: [number, number][], progress: number): [number, number][] {
  if (coords.length < 2 || progress >= 1) return coords;
  const target = progress * (coords.length - 1);
  const i = Math.floor(target);
  const frac = target - i;
  const sliced = coords.slice(0, i + 1);
  const a = coords[i];
  const b = coords[i + 1];
  if (a && b) {
    sliced.push([a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac]);
  }
  return sliced;
}

// Solid = observed, dashed = inferred (A*-bridged) — verbatim requirement,
// TEAM.md §8 / FRONTEND_BLUEPRINT.md §5. Observed points are clickable markers
// showing ts + outcome; healed:true segments get a visible badge, not just an
// identical dot, per FRONTEND_BLUEPRINT.md §5's explicit "don't let it render
// identically to a normal segment" requirement.
export function TrajectoryLayer({ trajectory }: TrajectoryLayerProps) {
  const [selected, setSelected] = useState<ObservedSegment | null>(null);
  const [drawProgress, setDrawProgress] = useState(0);

  // Defends against a backend that returns a well-formed shape but bad
  // numbers (missing/null lat/lon) — react-map-gl throws "Invalid LngLat
  // object: (NaN, NaN)" and takes the whole map down if these ever reach a
  // Marker/Popup/LineString uncoerced. Not an API contract change: this is
  // pure frontend robustness against a still-unwired backend.
  const isFiniteCoord = (lon: unknown, lat: unknown): boolean =>
    typeof lon === "number" && typeof lat === "number" && Number.isFinite(lon) && Number.isFinite(lat);

  const observed = trajectory.segments.filter(
    (s): s is ObservedSegment => s.type === "observed" && isFiniteCoord(s.lon, s.lat),
  );
  const observedCoords: [number, number][] = useMemo(
    () => observed.map((s) => [s.lon, s.lat]),
    [observed],
  );
  const inferredSegments = trajectory.segments.filter(
    (s): s is Extract<typeof s, { type: "inferred" }> =>
      s.type === "inferred" &&
      Array.isArray(s.path) &&
      s.path.length > 0 &&
      s.path.every((pt) => Array.isArray(pt) && isFiniteCoord(pt[0], pt[1])),
  );

  useEffect(() => {
    setDrawProgress(0);
    const start = performance.now();
    const durationMs = 1200;
    let frame: number;
    function tick(now: number) {
      const progress = Math.min(1, (now - start) / durationMs);
      setDrawProgress(progress);
      if (progress < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [observedCoords]);

  const drawnCoords = sliceLine(observedCoords, drawProgress);

  return (
    <>
      <Source
        id="trajectory-observed"
        type="geojson"
        data={{
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: drawnCoords },
        }}
      >
        <Layer
          id="trajectory-observed-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{ "line-color": "#d97e2c", "line-width": 3 }}
        />
      </Source>
      {drawProgress >= 1 &&
        inferredSegments.map((segment, i) => (
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

      {observed.map((segment, i) => {
        const revealAt = observed.length > 1 ? i / (observed.length - 1) : 0;
        if (drawProgress < revealAt) return null;
        return (
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
              className={`relative flex size-3.5 animate-in zoom-in items-center justify-center rounded-full ring-2 transition-transform duration-200 hover:scale-125 ${
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
        );
      })}

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
