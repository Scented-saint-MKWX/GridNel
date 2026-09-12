"use client";

import { useEffect, useState } from "react";
import Map, { Marker } from "react-map-gl";
import { Camera as CameraIcon, MapPinOff } from "lucide-react";
import "mapbox-gl/dist/mapbox-gl.css";
import type { Camera } from "@/lib/cameras";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

interface CityMapProps {
  children?: React.ReactNode;
  onCameraClick?: (camera: Camera) => void;
  flashingCameraId?: string | null;
}

// Camera positions come from db/cameras.json via /api/cameras — never
// hardcoded here. See CLAUDE.md "No hardcoded camera coordinates". When the
// seed is empty (P3 hasn't populated it yet), render an honest empty state —
// never fake markers to look complete (per the master prompt's explicit rule).
export function CityMap({ children, onCameraClick, flashingCameraId }: CityMapProps) {
  const [cameras, setCameras] = useState<Camera[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/cameras")
      .then((res) => res.json())
      .then((data: Camera[]) => {
        if (!cancelled) setCameras(data);
      })
      .catch(() => {
        if (!cancelled) setCameras([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="relative size-full">
      <Map
        mapboxAccessToken={MAPBOX_TOKEN}
        initialViewState={{ longitude: 77.209, latitude: 28.6139, zoom: 11 }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        style={{ width: "100%", height: "100%" }}
      >
        {(cameras ?? []).map((camera) => {
          const isFlashing = camera.camera_id === flashingCameraId;
          return (
            <Marker
              key={camera.camera_id}
              longitude={camera.lon}
              latitude={camera.lat}
              onClick={() => onCameraClick?.(camera)}
            >
              <button
                type="button"
                className="group relative flex size-3 items-center justify-center rounded-full bg-analyst ring-2 ring-analyst/30"
                aria-label={camera.camera_id}
              >
                {isFlashing && (
                  <span className="absolute inset-0 rounded-full bg-alert animate-pulse-ring" />
                )}
                <span
                  className={`relative size-3 rounded-full ${isFlashing ? "bg-alert" : "bg-analyst"}`}
                />
                <CameraIcon
                  className={`absolute -top-5 size-3 transition-colors ${
                    isFlashing ? "text-alert" : "text-analyst/70 group-hover:text-analyst"
                  }`}
                />
              </button>
            </Marker>
          );
        })}
        {children}
      </Map>

      {cameras !== null && cameras.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="glass flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm text-muted-foreground">
            <MapPinOff className="size-4" />
            No cameras loaded yet — db/cameras.json is empty
          </div>
        </div>
      )}
    </div>
  );
}
