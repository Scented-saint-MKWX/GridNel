"use client";

import { useEffect, useMemo, useState } from "react";
import { Popup, Source, Layer, useMap, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import type { Route } from "@/types/analytics";
import { resolveRoadCoordinate, smoothPath } from "@/lib/roads";
import { ROUTE_RANK_COLORS } from "@/lib/colors";

interface RoutesLayerProps {
  routes: Route[];
  roadCoordinateIndex: Map<string, [number, number]>;
  topN?: number;
}

type RankedRoute = Route & { rank: number; path: [number, number][] };

// Real GET /analytics/routes (Nawfal, 2026-09-13, TEAM.md §4). Master prompt
// v12 Phase 1: cap to the top N by vehicle_count (client-side — no backend
// change needed for the "too many overlapping lines" issue) and encode rank
// continuously via width+opacity+hue instead of scattering floating "#N"
// number badges over the map. Rank/volume/speed detail moved to a hover
// tooltip anchored to the actual cursor position; the on-map label is
// dropped entirely in favor of the ranked list panel in analytics/page.tsx.
export function RoutesLayer({ routes, roadCoordinateIndex, topN = 12 }: RoutesLayerProps) {
  const [hovered, setHovered] = useState<{ route: RankedRoute; lngLat: [number, number] } | null>(
    null,
  );

  const { linesData, maxCount, byId } = useMemo(() => {
    const ranked: RankedRoute[] = [...routes]
      .sort((a, b) => b.vehicle_count - a.vehicle_count)
      .slice(0, topN)
      .map((r, i) => ({
        ...r,
        rank: i + 1,
        // Real concatenated path vertices when available (DECISIONS.md #8)
        // — falls back to per-road-id centroid resolution for routes
        // predating the geometry field or missing a direct road_edges hop,
        // smoothed into a Catmull-Rom spline (lib/roads.ts) so the fallback
        // doesn't read as an obviously synthetic sharp-angled polyline next
        // to routes that do have real OSM geometry.
        path: (r.geometry && r.geometry.length >= 2
          ? r.geometry
          : smoothPath(
              r.road_sequence
                .map((roadId) => resolveRoadCoordinate(roadCoordinateIndex, roadId))
                .filter((p): p is [number, number] => p !== null),
            )) as [number, number][],
      }));

    const maxCount = Math.max(...ranked.map((r) => r.vehicle_count), 1);
    const byId = new Map(ranked.map((r) => [r.route_id, r]));

    const linesData = {
      type: "FeatureCollection" as const,
      features: ranked
        .filter((r) => r.path.length >= 2)
        .map((r) => ({
          type: "Feature" as const,
          properties: { route_id: r.route_id, rank: r.rank, vehicle_count: r.vehicle_count },
          geometry: { type: "LineString" as const, coordinates: r.path },
        })),
    };

    return { linesData, maxCount, byId };
  }, [routes, roadCoordinateIndex, topN]);

  function handleHover(e: MapLayerMouseEvent) {
    const feature = e.features?.[0];
    const routeId = feature?.properties?.route_id as string | undefined;
    const route = routeId ? byId.get(routeId) : undefined;
    setHovered(route ? { route, lngLat: [e.lngLat.lng, e.lngLat.lat] } : null);
  }

  return (
    <>
      <Source id="analytics-routes" type="geojson" data={linesData}>
        <Layer
          id="analytics-routes-line"
          type="line"
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            // Rank #1 renders thick and fully opaque; rank #N (the cap)
            // renders thin and mostly transparent — continuous, not a flat
            // line plus a disconnected badge.
            "line-width": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 1.5, maxCount, 8],
            "line-opacity": ["interpolate", ["linear"], ["get", "vehicle_count"], 0, 0.3, maxCount, 0.95],
            "line-color": [
              "interpolate",
              ["linear"],
              ["get", "vehicle_count"],
              0,
              ROUTE_RANK_COLORS.low,
              maxCount * 0.5,
              ROUTE_RANK_COLORS.mid,
              maxCount,
              ROUTE_RANK_COLORS.top,
            ],
          }}
        />
      </Source>

      <RoutesHoverHandler onHover={handleHover} />

      {hovered && (
        <Popup
          longitude={hovered.lngLat[0]}
          latitude={hovered.lngLat[1]}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          className="[&_.maplibregl-popup-content]:!bg-surface-raised [&_.maplibregl-popup-content]:!rounded-lg [&_.maplibregl-popup-content]:!border [&_.maplibregl-popup-content]:!border-white/10 [&_.maplibregl-popup-content]:!px-2.5 [&_.maplibregl-popup-content]:!py-1.5"
        >
          <div className="space-y-0.5 text-xs">
            <div className="data-mono font-semibold" style={{ color: ROUTE_RANK_COLORS.top }}>
              #{hovered.route.rank} · {hovered.route.vehicle_count} vehicles
            </div>
            <div className="data-mono text-muted-foreground">
              {hovered.route.average_speed_kmh.toFixed(0)} km/h avg
            </div>
          </div>
        </Popup>
      )}
    </>
  );
}

function RoutesHoverHandler({ onHover }: { onHover: (e: MapLayerMouseEvent) => void }) {
  const { current: map } = useMap();

  useEffect(() => {
    if (!map) return;
    const handler = (e: MapLayerMouseEvent) => onHover(e);
    const clear = () => onHover({ features: [] } as unknown as MapLayerMouseEvent);
    map.on("mousemove", "analytics-routes-line", handler);
    map.on("mouseleave", "analytics-routes-line", clear);
    return () => {
      map.off("mousemove", "analytics-routes-line", handler);
      map.off("mouseleave", "analytics-routes-line", clear);
    };
  }, [map, onHover]);

  return null;
}
