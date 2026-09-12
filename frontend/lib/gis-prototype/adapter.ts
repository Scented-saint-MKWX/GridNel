import type { Camera } from "@/lib/cameras";
import type { RoadSegment, RouteSummary, CongestionLevel } from "@/types/gis-prototype";

// Client-side join for the GIS prototypes, isolated behind this one file per
// DECISIONS.md #4's explicit requirement: "isolated behind a swappable
// type/adapter so it's a small change either way once the real shape is
// confirmed." The team-chat notes describe a trajectory shape with camera/
// timestamp and NO lat/lon — if the real backend ever ships that shape for
// these prototype endpoints, only this file's lookup logic needs to change,
// not every consumer component.
//
// Today, with no real /analytics/segments, /analytics/routes, or OD endpoint
// in TEAM.md §4.4 (OD is an explicit L1 non-goal, TEAM.md §11), this adapter
// only resolves camera_id -> [lon, lat] against db/cameras.json for mock
// fixtures. Swap the body of resolveNode() when a real endpoint lands.

export function buildCameraIndex(cameras: Camera[]): Map<string, Camera> {
  return new Map(cameras.map((c) => [c.camera_id, c]));
}

export function resolveNode(
  cameraIndex: Map<string, Camera>,
  cameraId: string,
): [number, number] | null {
  const camera = cameraIndex.get(cameraId);
  return camera ? [camera.lon, camera.lat] : null;
}

// Industry-standard congestion coloring — TomTom/Mapbox Traffic/ArcGIS
// convention, logged in DECISIONS.md #4 so nobody re-invents a scheme.
export const CONGESTION_COLORS: Record<CongestionLevel, string> = {
  low: "#22c55e",
  moderate: "#eab308",
  heavy: "#f97316",
  severe: "#ef4444",
};

export function congestionFromVehicleCount(count: number): CongestionLevel {
  if (count < 20) return "low";
  if (count < 45) return "moderate";
  if (count < 75) return "heavy";
  return "severe";
}

export type { RoadSegment, RouteSummary };
