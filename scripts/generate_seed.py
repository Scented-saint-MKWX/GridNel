"""Generate a real-road-network seed for db/cameras.json + db/road_edges.json.

Master prompt v11, authorized by Wahid alone (DECISIONS.md #8, NOT team
consensus — cameras.json is otherwise frozen per TEAM.md §4.3/§5). Replaces
v10's synthetic-grid generator (uniform lattice, straight-line edges) with
one built from the real Delhi/New Delhi/Noida/Ghaziabad OSM road network:

  - Phase 1: fetch the real drivable street graph for the demo's bounding
    box via the Overpass API, ONCE, offline, as a preprocessing step. The
    running app (fog_sim, api, frontend) has zero runtime dependency on
    OSM/Overpass — this script only ever runs by hand, ahead of a demo, and
    its raw fetch is cached to disk (--raw-cache) so re-running it to tweak
    camera count doesn't re-hit the network at all.
  - Phase 2: pick ~N real intersection nodes as camera sites, preferring
    higher-degree / higher-betweenness-centrality nodes (real junctions)
    over arbitrary points, biased toward denser coverage in central Delhi
    and sparser coverage toward the Noida/Ghaziabad periphery.
  - Phase 3: build road_edges with REAL edge geometry (the OSM way's actual
    vertex list between adjacent camera nodes, not a straight line), and
    assign congestion with spatial plausibility (central segments skew
    HIGH, peripheral skew LOW) via speed_limit_kmh.
  - Phase 4: precompute realistic "busiest routes" as real networkx
    shortest paths between realistic origin/destination camera pairs,
    storing the full concatenated real path geometry (every intermediate
    edge's real vertices), not just start/end points.

Note on osmnx: `osmnx.graph_from_bbox()` internally monkeypatches
`socket.getaddrinfo` to pin overpass-api.de to one DNS-resolved IP (its
`_config_dns`, meant to avoid hitting different servers in the round-robin
pool mid-session). In this environment that pinned IP was unreachable while
plain `requests` calls (which re-resolve per-request) succeeded immediately
and consistently. So this script talks to Overpass directly with
`requests` and hands the raw response to osmnx's internal
`osmnx.graph._create_graph()` / `osmnx.simplify_graph()` to get a real
networkx graph — it still uses osmnx/networkx for all the actual graph
work, it just avoids osmnx's own DNS pinning for the HTTP leg.

Run (fetches from Overpass, ~1-3 min, then caches):
    python scripts/generate_seed.py --cameras 300

Re-run against the cached fetch (no network) after changing --cameras:
    python scripts/generate_seed.py --cameras 250 --raw-cache db/.osm_raw_cache.json

Writes:
  db/cameras.json     — camera_id, lat, lon, zone, road_node_id (same shape
                        as the original frozen 6-camera seed)
  db/road_edges.json  — from_node, to_node, length_m, speed_limit_kmh,
                        typical_speeds, geometry ([[lon,lat],...], real OSM
                        vertices) — geometry is new, see DECISIONS.md #8
  db/routes.json      — precomputed busiest-route candidates: route_id,
                        road_sequence, geometry (full concatenated real
                        path vertices) — consumed by db/seed.py to seed
                        realistic sighting sequences instead of random walks

Does not touch plaintext plate data or the hashing/role-gating path.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMERAS_PATH = REPO_ROOT / "db" / "cameras.json"
ROAD_EDGES_PATH = REPO_ROOT / "db" / "road_edges.json"
ROUTES_PATH = REPO_ROOT / "db" / "routes.json"
DEFAULT_RAW_CACHE = REPO_ROOT / "db" / ".osm_raw_cache.json"

RANDOM_SEED = 42

# Delhi/New Delhi (dense center) through Noida/Ghaziabad (sparser periphery)
# — the same real-world area the frozen 6-camera seed and v10's synthetic
# grid were both centered on. (south, west, north, east) for Overpass bbox.
BBOX = (28.35, 77.00, 28.85, 77.55)
CENTER_LAT = 28.6139
CENTER_LON = 77.2090

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = f"""
[out:json][timeout:180];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|unclassified)$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
(._;>;);
out body;
"""

ZONES = ["central", "north", "south", "east", "west"]


def fetch_raw_osm(raw_cache: Path, force_refetch: bool) -> dict[str, Any]:
    if raw_cache.exists() and not force_refetch:
        print(f"[generate_seed] using cached OSM fetch -> {raw_cache}")
        with open(raw_cache, encoding="utf-8") as f:
            return json.load(f)

    import requests  # local import: only needed for the offline fetch step

    print(f"[generate_seed] fetching real OSM road network for bbox {BBOX} ...")
    resp = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=240,
        headers={"User-Agent": "SentinelGrid-seedgen/1.0 (hackathon demo, offline preprocessing)"},
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"[generate_seed] fetched {len(data.get('elements', []))} OSM elements")

    raw_cache.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_cache, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"[generate_seed] cached raw fetch -> {raw_cache} (re-runs won't hit the network)")
    return data


def build_graph(raw_osm: dict[str, Any]):
    """Real networkx graph via osmnx's graph-building internals — no
    network access happens here, raw_osm is already-fetched Overpass JSON."""
    import networkx as nx  # noqa: F401  (imported for type clarity / availability check)
    import osmnx as ox
    import osmnx.graph as oxg

    G = oxg._create_graph([raw_osm], bidirectional=True)
    G = ox.simplify_graph(G)
    G = ox.truncate.largest_component(G, strongly=True)
    print(f"[generate_seed] simplified graph: {len(G.nodes)} nodes, {len(G.edges)} edges "
          f"(largest strongly-connected component)")
    return G


def zone_for(lat: float, lon: float) -> str:
    if lat > CENTER_LAT + 0.03:
        return "north"
    if lat < CENTER_LAT - 0.03:
        return "south"
    if lon < CENTER_LON - 0.03:
        return "west"
    if lon > CENTER_LON + 0.03:
        return "east"
    return "central"


def distance_from_center_km(lat: float, lon: float) -> float:
    meters_per_lat_deg = 111_320
    meters_per_lon_deg = 111_320 * math.cos(math.radians(CENTER_LAT))
    dlat = (lat - CENTER_LAT) * meters_per_lat_deg
    dlon = (lon - CENTER_LON) * meters_per_lon_deg
    return math.hypot(dlat, dlon) / 1000.0


def select_camera_nodes(G, num_cameras: int, seed: int) -> list[int]:
    """Prefer real junctions (higher degree, higher betweenness centrality)
    over arbitrary points, biased toward denser central coverage and
    sparser peripheral coverage — matching how real ANPR deployments
    cluster around major intersections/checkpoints rather than uniform
    spacing (master prompt v11 Phase 2).

    Full-graph betweenness centrality (334k nodes / 939k edges) is
    computationally infeasible for a one-time-but-still-interactive seed
    step even sampled — this restricts the expensive centrality
    computation to a bounded degree>=3 junction subgraph (still tens of
    thousands of real intersections) and further caps the sample size,
    trading some ranking precision for the step actually finishing."""
    import networkx as nx

    rng = random.Random(seed)
    degrees = dict(G.degree())

    junction_nodes = [n for n, deg in degrees.items() if deg >= 3]
    print(f"[generate_seed] {len(junction_nodes)} real junction nodes (degree >= 3) "
          f"out of {len(G.nodes)} total")

    # Cap the subgraph centrality runs on: prefer highest-degree junctions
    # first (cheap proxy for importance) so the centrality-eligible pool is
    # already skewed toward real arterial crossings before the expensive
    # step even starts.
    MAX_CENTRALITY_NODES = 15000
    junction_nodes.sort(key=lambda n: -degrees[n])
    centrality_pool = junction_nodes[:MAX_CENTRALITY_NODES]
    # Betweenness needs the full graph's connectivity context (paths can
    # route through non-pool nodes), so this runs on G itself but only
    # samples sources/targets from the pool — keeps the O(k) factor bounded
    # to junctions we'd actually consider as camera sites. Each source is
    # one weighted Dijkstra over a 334k-node/939k-edge graph (~1.8s
    # measured), so k is kept small enough to finish this one-time offline
    # step in a few minutes rather than tens of minutes; degree is still
    # the dominant, cheap real-junction signal in the final score.
    k_sources = min(150, len(centrality_pool))
    print(f"[generate_seed] estimating betweenness centrality "
          f"(k={k_sources} sample sources, over {len(centrality_pool)}-junction pool) ...")
    centrality = nx.betweenness_centrality_subset(
        G,
        sources=rng.sample(centrality_pool, k_sources),
        targets=rng.sample(centrality_pool, k_sources),
        weight="length",
    )

    candidates = []
    for node_id in centrality_pool:
        data = G.nodes[node_id]
        lat, lon = data["y"], data["x"]
        deg = degrees.get(node_id, 0)
        score = centrality.get(node_id, 0.0) * 0.7 + (deg / 8.0) * 0.3
        candidates.append((node_id, lat, lon, score))

    if not candidates:
        raise RuntimeError("no junction candidates found — check bbox/highway filter")

    # Central-biased density: give every candidate a weight combining its
    # junction "importance" score with an inverse-distance-from-center
    # falloff, so central Delhi is denser and Noida/Ghaziabad periphery is
    # sparser, matching a real deployment's coverage pattern rather than
    # uniform spacing across the whole bbox.
    weighted: list[tuple[int, float, float, float]] = []
    for node_id, lat, lon, score in candidates:
        dist_km = distance_from_center_km(lat, lon)
        density_falloff = 1.0 / (1.0 + (dist_km / 8.0) ** 2)
        weight = (score + 0.01) * density_falloff
        weighted.append((node_id, lat, lon, weight))

    # Weighted sample without replacement, with minimum spacing so cameras
    # don't cluster on adjacent nodes of the same physical intersection.
    weighted.sort(key=lambda t: t[3], reverse=True)
    pool = weighted[: max(num_cameras * 8, 2000)]  # only consider the strongest candidates
    rng.shuffle(pool)  # break ties/ordering bias before greedy min-spacing pass

    min_spacing_deg = 0.0015  # ~150m, avoids two cameras on the same junction
    chosen: list[tuple[int, float, float]] = []
    for node_id, lat, lon, _weight in sorted(pool, key=lambda t: -t[3]):
        if len(chosen) >= num_cameras:
            break
        too_close = any(
            abs(lat - c_lat) < min_spacing_deg and abs(lon - c_lon) < min_spacing_deg
            for _, c_lat, c_lon in chosen
        )
        if too_close:
            continue
        chosen.append((node_id, lat, lon))

    if len(chosen) < num_cameras:
        print(f"[generate_seed] WARNING: only found {len(chosen)}/{num_cameras} "
              f"well-spaced junctions, proceeding with {len(chosen)}")

    return [node_id for node_id, _, _ in chosen]


def edge_geometry(G, u: int, v: int, key: int = 0) -> list[list[float]]:
    """Real vertex list [[lon,lat],...] for one graph edge, endpoints
    included. Falls back to a straight 2-point line only when OSM stored
    no intermediate shape for this particular way segment (a genuinely
    straight road, not a synthetic simplification)."""
    data = G.get_edge_data(u, v)
    if data is None:
        data = G.get_edge_data(v, u)
    if data is None:
        return []
    edge_data = data.get(key) or next(iter(data.values()))
    geom = edge_data.get("geometry")
    if geom is not None:
        coords = [[round(x, 6), round(y, 6)] for x, y in geom.coords]
        return coords
    u_data, v_data = G.nodes[u], G.nodes[v]
    return [
        [round(u_data["x"], 6), round(u_data["y"], 6)],
        [round(v_data["x"], 6), round(v_data["y"], 6)],
    ]


def typical_speeds_for_hour() -> dict[str, int]:
    return {str(h): (25 if 7 <= h <= 10 or 17 <= h <= 20 else 40) for h in range(24)}


def congestion_speed_limit(lat: float, lon: float, base_limit: int, rng: random.Random) -> int:
    """Spatial plausibility for congestion (master prompt v11 Phase 3):
    denser central segments get a lower effective speed limit (reads as
    HIGH congestion via api/analytics.py's ratio-to-speed-limit check),
    peripheral segments keep their nominal limit (reads as LOW)."""
    dist_km = distance_from_center_km(lat, lon)
    if dist_km < 5:
        return max(20, base_limit - rng.choice([15, 20, 25]))
    if dist_km < 12:
        return max(25, base_limit - rng.choice([0, 5, 10]))
    return base_limit


def build_seed(G, camera_nodes: list[int], seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)

    cameras: list[dict] = []
    node_to_camera: dict[int, str] = {}
    for i, node_id in enumerate(camera_nodes):
        data = G.nodes[node_id]
        lat, lon = data["y"], data["x"]
        camera_id = f"CAM_{i + 1:03d}"
        road_node_id = f"N{i + 1}"
        node_to_camera[node_id] = road_node_id
        cameras.append(
            {
                "camera_id": camera_id,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "zone": zone_for(lat, lon),
                "road_node_id": road_node_id,
            }
        )

    camera_node_set = set(camera_nodes)
    typical_speeds = typical_speeds_for_hour()

    # Connect each pair of camera nodes that has a real shortest path
    # between them in the underlying road graph, storing that path's real
    # geometry as the edge (so consecutive cameras are "adjacent" in the
    # same sense a real ANPR deployment's neighboring checkpoints are —
    # connected by an actual stretch of real road, not a straight line).
    import networkx as nx

    print(f"[generate_seed] computing real shortest paths between {len(camera_nodes)} camera nodes ...")
    edges: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    # For tractability, connect each camera to its K nearest (by real graph
    # distance) other cameras rather than an all-pairs shortest-path search
    # (which is O(n^2) Dijkstra calls over a 300k-node graph).
    K_NEAREST = 4
    for node_id in camera_nodes:
        try:
            lengths, paths = nx.single_source_dijkstra(G, node_id, weight="length", cutoff=6000)
        except nx.NetworkXNoPath:
            continue
        reachable_cameras = [
            (other, lengths[other]) for other in camera_node_set if other in lengths and other != node_id
        ]
        reachable_cameras.sort(key=lambda t: t[1])
        for other_node, length_m in reachable_cameras[:K_NEAREST]:
            from_cam, to_cam = node_to_camera[node_id], node_to_camera[other_node]
            if (from_cam, to_cam) in seen_pairs or (to_cam, from_cam) in seen_pairs:
                continue
            seen_pairs.add((from_cam, to_cam))
            seen_pairs.add((to_cam, from_cam))

            path = paths[other_node]
            geometry: list[list[float]] = []
            for a, b in zip(path[:-1], path[1:]):
                seg = edge_geometry(G, a, b)
                if geometry and seg and geometry[-1] == seg[0]:
                    geometry.extend(seg[1:])
                else:
                    geometry.extend(seg)

            u_data = G.nodes[node_id]
            mid_lat, mid_lon = u_data["y"], u_data["x"]
            base_limit = rng.choice([30, 40, 45, 50, 60])
            speed_limit = congestion_speed_limit(mid_lat, mid_lon, base_limit, rng)

            for from_node, to_node, geom in (
                (from_cam, to_cam, geometry),
                (to_cam, from_cam, list(reversed(geometry))),
            ):
                edges.append(
                    {
                        "from_node": from_node,
                        "to_node": to_node,
                        "length_m": round(length_m, 1),
                        "speed_limit_kmh": speed_limit,
                        "typical_speeds": typical_speeds,
                        "geometry": geom,
                    }
                )

    return cameras, edges


def build_routes(cameras: list[dict], edges: list[dict], num_routes: int, seed: int) -> list[dict]:
    """Precomputed 'busiest routes' as real multi-hop shortest paths over
    the camera-node graph we just built (master prompt v11 Phase 4) —
    stores the full concatenated real geometry, not just endpoints."""
    import networkx as nx

    rng = random.Random(seed)
    RG = nx.DiGraph()
    for e in edges:
        RG.add_edge(e["from_node"], e["to_node"], length_m=e["length_m"], geometry=e["geometry"])

    road_nodes = [c["road_node_id"] for c in cameras]
    routes: list[dict] = []
    attempts = 0
    seen_routes: set[tuple[str, ...]] = set()
    while len(routes) < num_routes and attempts < num_routes * 20:
        attempts += 1
        origin, dest = rng.sample(road_nodes, 2)
        try:
            path = nx.shortest_path(RG, origin, dest, weight="length_m")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        if len(path) < 3 or len(path) > 12:
            continue
        key = tuple(path)
        if key in seen_routes:
            continue
        seen_routes.add(key)

        geometry: list[list[float]] = []
        for a, b in zip(path[:-1], path[1:]):
            seg = RG[a][b]["geometry"]
            if geometry and seg and geometry[-1] == seg[0]:
                geometry.extend(seg[1:])
            else:
                geometry.extend(seg)

        routes.append(
            {
                "route_id": f"route_{len(routes) + 1}",
                "road_sequence": path,
                "geometry": geometry,
            }
        )

    return routes


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a real-road-network camera seed")
    parser.add_argument("--cameras", type=int, default=300, help="target camera count")
    parser.add_argument("--routes", type=int, default=20, help="precomputed busiest-route candidates")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="deterministic RNG seed")
    parser.add_argument(
        "--raw-cache",
        type=Path,
        default=DEFAULT_RAW_CACHE,
        help="path to cache the raw Overpass fetch (default db/.osm_raw_cache.json)",
    )
    parser.add_argument(
        "--force-refetch",
        action="store_true",
        help="ignore any existing raw cache and hit Overpass again",
    )
    args = parser.parse_args()

    raw_osm = fetch_raw_osm(args.raw_cache, args.force_refetch)
    G = build_graph(raw_osm)
    camera_nodes = select_camera_nodes(G, args.cameras, args.seed)
    cameras, edges = build_seed(G, camera_nodes, args.seed)
    routes = build_routes(cameras, edges, args.routes, args.seed)

    CAMERAS_PATH.write_text(json.dumps(cameras, indent=2) + "\n", encoding="utf-8")
    ROAD_EDGES_PATH.write_text(json.dumps(edges, indent=2) + "\n", encoding="utf-8")
    ROUTES_PATH.write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")

    print(f"[generate_seed] wrote {len(cameras)} cameras -> {CAMERAS_PATH}")
    print(f"[generate_seed] wrote {len(edges)} directed road edges (real geometry) -> {ROAD_EDGES_PATH}")
    print(f"[generate_seed] wrote {len(routes)} precomputed routes (real geometry) -> {ROUTES_PATH}")


if __name__ == "__main__":
    main()
