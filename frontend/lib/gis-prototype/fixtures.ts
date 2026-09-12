import { MOCK_CAMERAS } from "@/lib/mock/fixtures";
import { congestionFromVehicleCount } from "@/lib/gis-prototype/adapter";
import type { RoadSegment, RouteSummary } from "@/types/gis-prototype";

// Mock fixtures for the Part 2 GIS prototypes — see DECISIONS.md #4. Built
// only from the six real seeded cameras/nodes (db/cameras.json via
// lib/mock/fixtures.ts's MOCK_CAMERAS), never invented coordinates, per
// CLAUDE.md "No hardcoded camera coordinates."

const nodeById = new Map(MOCK_CAMERAS.map((c) => [c.road_node_id, c]));

const EDGES: [string, string, number][] = [
  ["N1", "N2", 18],
  ["N2", "N3", 52],
  ["N3", "N4", 34],
  ["N4", "N5", 81],
  ["N5", "N6", 27],
  ["N1", "N6", 63],
];

export function mockRoadSegments(): RoadSegment[] {
  return EDGES.map(([from_node, to_node, vehicle_count]) => {
    const from = nodeById.get(from_node)!;
    const to = nodeById.get(to_node)!;
    return {
      from_node,
      to_node,
      from: [from.lon, from.lat],
      to: [to.lon, to.lat],
      vehicle_count,
      congestion: congestionFromVehicleCount(vehicle_count),
    };
  });
}

export function mockRoutes(): RouteSummary[] {
  const routes: { nodes: string[]; vehicle_count: number }[] = [
    { nodes: ["N1", "N2", "N3"], vehicle_count: 96 },
    { nodes: ["N4", "N5", "N6"], vehicle_count: 71 },
    { nodes: ["N1", "N6"], vehicle_count: 63 },
  ];
  return routes
    .sort((a, b) => b.vehicle_count - a.vehicle_count)
    .map((r, i) => ({
      route_id: `route_${i + 1}`,
      node_path: r.nodes,
      path: r.nodes.map((id) => {
        const c = nodeById.get(id)!;
        return [c.lon, c.lat] as [number, number];
      }),
      vehicle_count: r.vehicle_count,
      rank: i + 1,
    }));
}
