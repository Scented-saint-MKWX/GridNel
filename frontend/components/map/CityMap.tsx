"use client";

import { useEffect, useState } from "react";
import Map, { Marker } from "react-map-gl";
import { Camera as CameraIcon } from "lucide-react";
import "mapbox-gl/dist/mapbox-gl.css";
import type { Camera } from "@/lib/cameras";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

interface CityMapProps {
  children?: React.ReactNode;
  onCameraClick?: (camera: Camera) => void;
}

// Camera positions come from db/cameras.json via /api/cameras — never
// hardcoded here. See CLAUDE.md "No hardcoded camera coordinates".
export function CityMap({ children, onCameraClick }: CityMapProps) {
  const [cameras, setCameras] = useState<Camera[]>([]);

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
    <Map
      mapboxAccessToken={MAPBOX_TOKEN}
      initialViewState={{ longitude: 77.209, latitude: 28.6139, zoom: 11 }}
      mapStyle="mapbox://styles/mapbox/dark-v11"
      style={{ width: "100%", height: "100%" }}
    >
      {cameras.map((camera) => (
        <Marker
          key={camera.camera_id}
          longitude={camera.lon}
          latitude={camera.lat}
          onClick={() => onCameraClick?.(camera)}
        >
          <button
            type="button"
            className="relative flex size-3 items-center justify-center rounded-full bg-analyst ring-2 ring-analyst/30"
            aria-label={camera.camera_id}
          >
            <CameraIcon className="absolute -top-5 size-3 text-analyst/70" />
          </button>
        </Marker>
      ))}
      {children}
    </Map>
  );
}
