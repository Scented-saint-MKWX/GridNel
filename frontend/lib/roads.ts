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
    if (!Number.isFinite(c.longitude) || !Number.isFinite(c.latitude)) continue;
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
  const coord = index.get(roadId);
  if (!coord || !Number.isFinite(coord[0]) || !Number.isFinite(coord[1])) return null;
  return coord;
}

// Smooths a polyline of road-id centroids into a Catmull-Rom spline — used
// as the fallback path for routes/OD flows that predate the real `geometry`
// field or are missing a direct road_edges hop (DECISIONS.md #8 covers
// roughly half of routes/OD in the current seed, so this fallback is
// visually load-bearing, not an edge case). Centroid-to-centroid straight
// segments read as obviously synthetic/robotic next to the real
// OSM-geometry paths on the same map (sharp angular kinks at every road_id
// boundary) — a Catmull-Rom spline passes through every original point
// exactly (so it stays faithful to the resolved road centroids) while
// interpolating a smooth curve between them, closer to how a real route
// bends through a road network. Master prompt v12 Phase 4 ("curves through
// the roads should be perfected, look as real as possible").
export function smoothPath(points: [number, number][], samplesPerSegment = 8): [number, number][] {
  if (points.length < 3) return points;
  const pt = (i: number): [number, number] => points[Math.max(0, Math.min(points.length - 1, i))]!;
  const out: [number, number][] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = pt(i - 1);
    const p1 = pt(i);
    const p2 = pt(i + 1);
    const p3 = pt(i + 2);
    const steps = i === points.length - 2 ? samplesPerSegment : samplesPerSegment - 1;
    for (let s = 0; s <= steps; s++) {
      const t = s / samplesPerSegment;
      const t2 = t * t;
      const t3 = t2 * t;
      const x =
        0.5 *
        (2 * p1[0] +
          (-p0[0] + p2[0]) * t +
          (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
          (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
      const y =
        0.5 *
        (2 * p1[1] +
          (-p0[1] + p2[1]) * t +
          (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
          (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
      out.push([x, y]);
    }
  }
  return out;
}
