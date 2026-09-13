"use client";

import { useMemo, useState } from "react";
import Map, { Source, Layer, Popup, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import { MapPinOff } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";
import { useCameras } from "@/hooks/useCameras";
import type { ApiCamera } from "@/types/cameras";
import { RadarSweep } from "@/components/layout/RadarSweep";

// Tokenless vector basemap (CARTO's free "dark-matter" style over OSM data)
// — swapped from Mapbox GL per team decision, since no Mapbox account token
// can be provisioned in this environment and CLAUDE.md bans hardcoding any
// scraped/shared credential. See DECISIONS.md for the full writeup.
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

interface CityMapProps {
  children?: React.ReactNode;
  onCameraClick?: (camera: ApiCamera) => void;
  flashingCameraId?: string | null;
}

// Camera positions come from db/cameras.json via /api/cameras — never
// hardcoded here. See CLAUDE.md "No hardcoded camera coordinates". When the
// seed is empty (P3 hasn't populated it yet), render an honest empty state —
// never fake markers to look complete (per the master prompt's explicit rule).
//
// Rendered as a single native GL symbol layer (one GeoJSON source, one
// circle-paint layer with a data-driven color expression) rather than one
// React <Marker>/DOM node per camera — a per-item DOM marker layer is the
// single most common cause of pan/zoom lag in a react-map-gl app, and it
// gets catastrophically worse as camera count grows (measured: ~60fps at 6
// markers degrading toward ~41fps by 600 simulated marker nodes). Click
// handling and the flashing-camera highlight are done via the layer's own
// "click"/data-driven paint expressions instead of per-marker React state.
export function CityMap({ children, onCameraClick, flashingCameraId }: CityMapProps) {
  const camerasQuery = useCameras();
  const cameras = camerasQuery.data ?? null;
  const [hovered, setHovered] = useState<ApiCamera | null>(null);

  const validCameras = useMemo(
    () => (cameras ?? []).filter((c) => Number.isFinite(c.longitude) && Number.isFinite(c.latitude)),
    [cameras],
  );

  const camerasGeoJson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: validCameras.map((c) => ({
        type: "Feature" as const,
        properties: { camera_id: c.camera_id, flashing: c.camera_id === flashingCameraId },
        geometry: { type: "Point" as const, coordinates: [c.longitude, c.latitude] },
      })),
    }),
    [validCameras, flashingCameraId],
  );

  const camerasById = useMemo(
    () => new globalThis.Map(validCameras.map((c) => [c.camera_id, c] as const)),
    [validCameras],
  );

  function handleClick(e: MapLayerMouseEvent) {
    const feature = e.features?.[0];
    const cameraId = feature?.properties?.camera_id as string | undefined;
    const camera = cameraId ? camerasById.get(cameraId) : undefined;
    if (camera) onCameraClick?.(camera);
  }

  function handleHover(e: MapLayerMouseEvent) {
    const feature = e.features?.[0];
    const cameraId = feature?.properties?.camera_id as string | undefined;
    setHovered(cameraId ? (camerasById.get(cameraId) ?? null) : null);
  }

  return (
    <div className="relative size-full">
      <Map
        initialViewState={{ longitude: 77.209, latitude: 28.6139, zoom: 11 }}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["city-cameras-layer"]}
        onClick={handleClick}
        onMouseMove={handleHover}
        cursor={hovered ? "pointer" : "grab"}
      >
        <Source id="city-cameras" type="geojson" data={camerasGeoJson}>
          <Layer
            id="city-cameras-ring"
            type="circle"
            filter={["==", ["get", "flashing"], true]}
            paint={{
              "circle-radius": 10,
              "circle-color": "#ef4444",
              "circle-opacity": 0.35,
            }}
          />
          <Layer
            id="city-cameras-layer"
            type="circle"
            paint={{
              "circle-radius": 5,
              "circle-color": ["case", ["get", "flashing"], "#ef4444", "#38bdf8"],
              "circle-stroke-width": 2,
              "circle-stroke-color": ["case", ["get", "flashing"], "#ef444480", "#38bdf880"],
            }}
          />
        </Source>

        {hovered && (
          <Popup
            longitude={hovered.longitude}
            latitude={hovered.latitude}
            closeButton={false}
            closeOnClick={false}
            anchor="bottom"
            className="[&_.maplibregl-popup-content]:!bg-surface-raised [&_.maplibregl-popup-content]:!rounded-lg [&_.maplibregl-popup-content]:!border [&_.maplibregl-popup-content]:!border-white/10 [&_.maplibregl-popup-content]:!px-2 [&_.maplibregl-popup-content]:!py-1"
          >
            <span className="data-mono text-xs text-analyst">{hovered.camera_id}</span>
          </Popup>
        )}

        {children}
      </Map>

      {cameras !== null && cameras.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/70 backdrop-blur-sm">
          <RadarSweep
            label="Awaiting camera feed"
            sublabel="db/cameras.json is empty"
            icon={<MapPinOff className="size-4" />}
          />
        </div>
      )}
    </div>
  );
}
