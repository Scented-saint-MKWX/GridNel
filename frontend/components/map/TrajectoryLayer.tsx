"use client";

import { useEffect, useMemo, useState } from "react";
import { Popup, Source, Layer, useMap, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import { Sparkles } from "lucide-react";
import type { ObservedSegment, Trajectory } from "@/types/tracking";
import { PlateThumbnail } from "@/components/map/PlateThumbnail";

const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === "true";

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

const isFiniteCoord = (lon: unknown, lat: unknown): boolean =>
  typeof lon === "number" && typeof lat === "number" && Number.isFinite(lon) && Number.isFinite(lat);

// Solid = observed, dashed = inferred (A*-bridged) — verbatim requirement,
// TEAM.md §8 / FRONTEND_BLUEPRINT.md §5. Observed points render as a single
// native GL circle layer (data-driven paint keyed on "healed"/"revealed"),
// not one React <Marker> per point — same per-item-DOM-node lag pattern as
// CityMap's camera markers, just bounded by trajectory length today. Click
// still opens the same detail Popup; healed segments still get the
// "self-corrected misread" badge, per FRONTEND_BLUEPRINT.md §5's explicit
// "don't let it render identically to a normal segment" requirement.
export function TrajectoryLayer({ trajectory }: TrajectoryLayerProps) {
  const [selected, setSelected] = useState<ObservedSegment | null>(null);
  const [drawProgress, setDrawProgress] = useState(0);

  // Defends against a backend that returns a well-formed shape but bad
  // numbers (missing/null lat/lon) — react-map-gl throws "Invalid LngLat
  // object: (NaN, NaN)" and takes the whole map down if these ever reach a
  // Marker/Popup/LineString uncoerced. Not an API contract change: this is
  // pure frontend robustness against a still-unwired backend.
  const observed = useMemo(
    () =>
      trajectory.segments.filter(
        (s): s is ObservedSegment => s.type === "observed" && isFiniteCoord(s.lon, s.lat),
      ),
    [trajectory.segments],
  );
  const observedCoords: [number, number][] = useMemo(
    () => observed.map((s) => [s.lon, s.lat]),
    [observed],
  );
  const inferredSegments = useMemo(
    () =>
      trajectory.segments.filter(
        (s): s is Extract<typeof s, { type: "inferred" }> =>
          s.type === "inferred" &&
          Array.isArray(s.path) &&
          s.path.length > 0 &&
          s.path.every((pt) => Array.isArray(pt) && isFiniteCoord(pt[0], pt[1])),
      ),
    [trajectory.segments],
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

  const observedLineData = useMemo(
    () => ({
      type: "Feature" as const,
      properties: {},
      geometry: { type: "LineString" as const, coordinates: drawnCoords },
    }),
    [drawnCoords],
  );

  const inferredData = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: inferredSegments.map((segment, i) => ({
        type: "Feature" as const,
        properties: { id: `${segment.from}-${segment.to}-${i}` },
        geometry: { type: "LineString" as const, coordinates: segment.path },
      })),
    }),
    [inferredSegments],
  );

  const observedPointsData = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: observed.map((segment, i) => {
        const revealAt = observed.length > 1 ? i / (observed.length - 1) : 0;
        return {
          type: "Feature" as const,
          properties: { index: i, healed: Boolean(segment.healed), revealAt },
          geometry: { type: "Point" as const, coordinates: [segment.lon, segment.lat] },
        };
      }),
    }),
    [observed],
  );

  const revealedPointsData = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: observedPointsData.features.filter((f) => drawProgress >= f.properties.revealAt),
    }),
    [observedPointsData, drawProgress],
  );

  function handlePointClick(e: MapLayerMouseEvent) {
    const feature = e.features?.[0];
    const index = feature?.properties?.index as number | undefined;
    if (index === undefined) return;
    e.originalEvent.stopPropagation();
    setSelected(observed[index] ?? null);
  }

  return (
    <>
      <Source id="trajectory-observed" type="geojson" data={observedLineData}>
        <Layer
          id="trajectory-observed-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{ "line-color": "#d97e2c", "line-width": 3 }}
        />
      </Source>

      {drawProgress >= 1 && (
        <Source id="trajectory-inferred" type="geojson" data={inferredData}>
          <Layer
            id="trajectory-inferred-line"
            type="line"
            layout={{ "line-cap": "round", "line-join": "round" }}
            paint={{ "line-color": "#a78bfa", "line-width": 2, "line-dasharray": [2, 2] }}
          />
        </Source>
      )}

      <Source id="trajectory-points" type="geojson" data={revealedPointsData}>
        <Layer
          id="trajectory-points-healed-halo"
          type="circle"
          filter={["==", ["get", "healed"], true]}
          paint={{ "circle-radius": 9, "circle-color": "#facc15", "circle-opacity": 0.3 }}
        />
        <Layer
          id="trajectory-points-layer"
          type="circle"
          paint={{
            "circle-radius": 6,
            "circle-color": ["case", ["get", "healed"], "#facc15", "#d97e2c"],
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff40",
          }}
        />
      </Source>

      {selected && (
        <Popup
          longitude={selected.lon}
          latitude={selected.lat}
          onClose={() => setSelected(null)}
          closeButton
          anchor="bottom"
          className="[&_.maplibregl-popup-content]:!bg-surface-raised [&_.maplibregl-popup-content]:!rounded-lg [&_.maplibregl-popup-content]:!border [&_.maplibregl-popup-content]:!border-white/10 [&_.maplibregl-popup-content]:!p-3 [&_.maplibregl-popup-tip]:!border-t-surface-raised"
        >
          <div className="space-y-1 text-xs">
            {MOCK_MODE && (
              <div className="mb-1.5">
                <PlateThumbnail plateText={trajectory.plate} />
              </div>
            )}
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
      <TrajectoryClickHandler onPointClick={handlePointClick} />
    </>
  );
}

// CityMap's own onClick is wired to its camera layer only; wiring this
// layer's clicks through CityMap would mean plumbing a second
// interactiveLayerIds/onClick pair through children just for this one
// child. Instead this component attaches its own click listener directly to
// the shared map instance (via react-map-gl's useMap context), scoped to
// its own layer ID — consistent with react-map-gl's documented pattern for
// per-layer interactivity without a single top-level handler enumerating
// every child layer.
function TrajectoryClickHandler({
  onPointClick,
}: {
  onPointClick: (e: MapLayerMouseEvent) => void;
}) {
  const { current: map } = useMap();

  useEffect(() => {
    if (!map) return;
    const handler = (e: MapLayerMouseEvent) => onPointClick(e);
    map.on("click", "trajectory-points-layer", handler);
    return () => {
      map.off("click", "trajectory-points-layer", handler);
    };
  }, [map, onPointClick]);

  return null;
}
