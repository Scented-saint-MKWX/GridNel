import type { ApiCamera } from "@/types/cameras";

// Nawfal's /analytics/od and /analytics/routes contracts (2026-09-13, TEAM.md
// §4) key origin/destination/road_sequence by road_id, not coordinates —
// unlike the trajectory shape, there's no lat/lon anywhere in those payloads.
// Real technical decision (flagged per the master prompt, not a silent
// guess): when multiple cameras share a road_id, we average their
// lat/lon into one centroid for that road. Alternative considered: take the
// first matching camera — rejected because averaging is stable regardless of
// /cameras' return order, and a road_id's "position" is inherently a
// same-road cluster, not one canonical point.
export function buildRoadCoordinateIndex(cameras: ApiCamera[]): Map<string, [number, number]> {
  const sums = new Map<string, { lon: number; lat: number; n: number }>();
  for (const c of cameras) {
    const entry = sums.get(c.road_id) ?? { lon: 0, lat: 0, n: 0 };
    entry.lon += c.longitude;
    entry.lat += c.latitude;
    entry.n += 1;
    sums.set(c.road_id, entry);
  }
  const index = new Map<string, [number, number]>();
  for (const [roadId, { lon, lat, n }] of sums) {
    index.set(roadId, [lon / n, lat / n]);
  }
  return index;
}

export function resolveRoadCoordinate(
  index: Map<string, [number, number]>,
  roadId: string,
): [number, number] | null {
  return index.get(roadId) ?? null;
}
