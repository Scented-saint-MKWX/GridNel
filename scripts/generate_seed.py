"""Generate a larger synthetic city grid for db/cameras.json + db/road_edges.json.

Master prompt v10 Phase 3: scale the seed dataset to roughly match testd's
~300-camera density, but built fresh against THIS project's actual schema
(db/schema.sql's cameras/road_edges tables, TEAM.md §4.3's camera shape) —
not copied from testd's incompatible shapes. Procedurally generates:

  - camera positions across a wider synthetic city grid (a grid of
    intersections, one camera per intersection, jittered off-grid slightly
    so it doesn't look like a literal lattice on the map)
  - a connected road-edge graph over those intersections (each camera's
    road_node_id connects to its grid neighbors, both directions, so A*
    bridging in api/graph.py always has a path to find)

Output is deterministic (fixed RANDOM_SEED) so re-running this script
doesn't silently reshuffle the demo's camera layout between runs. Run:

    python scripts/generate_seed.py --cameras 300

Writes db/cameras.json (same shape as the original 6-camera frozen seed:
camera_id, lat, lon, zone, road_node_id) and db/road_edges.json (consumed by
db/seed.py instead of its previous hardcoded 14-edge list). Does not touch
plaintext plate data or the hashing/role-gating path at all — those are
untouched by dataset size per the master prompt's explicit constraint.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMERAS_PATH = REPO_ROOT / "db" / "cameras.json"
ROAD_EDGES_PATH = REPO_ROOT / "db" / "road_edges.json"

RANDOM_SEED = 42

# Roughly Delhi-area, matching the original 6-camera seed's real-world
# location (TEAM.md §4.3's frozen cameras were centered near 28.61N 77.21E)
# so the demo's basemap view stays centered on populated map tiles.
CENTER_LAT = 28.6139
CENTER_LON = 77.2090

# Grid spacing in degrees, tuned so a ~17x18 grid spans a plausible
# metro-area footprint (~15km across) rather than either a single
# intersection or a whole state.
LAT_STEP = 0.008
LON_STEP = 0.009

ZONES = ["central", "north", "south", "east", "west"]


def zone_for(row: int, col: int, rows: int, cols: int) -> str:
    if row < rows * 0.3:
        return "north"
    if row > rows * 0.7:
        return "south"
    if col < cols * 0.3:
        return "west"
    if col > cols * 0.7:
        return "east"
    return "central"


def typical_speeds_for_hour() -> dict[str, int]:
    return {str(h): (25 if 7 <= h <= 10 or 17 <= h <= 20 else 40) for h in range(24)}


def generate(num_cameras: int, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)

    cols = max(1, round(math.sqrt(num_cameras * 1.1)))
    rows = math.ceil(num_cameras / cols)

    cameras: list[dict] = []
    node_grid: dict[tuple[int, int], str] = {}
    count = 0
    for row in range(rows):
        for col in range(cols):
            if count >= num_cameras:
                break
            node_id = f"N{count + 1}"
            jitter_lat = rng.uniform(-0.15, 0.15) * LAT_STEP
            jitter_lon = rng.uniform(-0.15, 0.15) * LON_STEP
            lat = CENTER_LAT + (row - rows / 2) * LAT_STEP + jitter_lat
            lon = CENTER_LON + (col - cols / 2) * LON_STEP + jitter_lon
            cameras.append(
                {
                    "camera_id": f"CAM_{count + 1:03d}",
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "zone": zone_for(row, col, rows, cols),
                    "road_node_id": node_id,
                }
            )
            node_grid[(row, col)] = node_id
            count += 1

    # Connected road-edge graph: every camera connects to its immediate grid
    # neighbors (right + down), both directions, so the resulting graph is
    # connected by construction (a grid graph is always connected) — A*
    # bridging always has a path between any two nodes, never an isolated
    # island. Length/speed are illustrative (same convention as the original
    # 6-node seed's comment), scaled from the grid step in degrees to meters.
    meters_per_lat_deg = 111_320
    meters_per_lon_deg = 111_320 * math.cos(math.radians(CENTER_LAT))
    typical_speeds = typical_speeds_for_hour()

    edges: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add_edge(a: tuple[int, int], b: tuple[int, int]) -> None:
        node_a = node_grid.get(a)
        node_b = node_grid.get(b)
        if node_a is None or node_b is None:
            return
        dlat = (b[0] - a[0]) * LAT_STEP
        dlon = (b[1] - a[1]) * LON_STEP
        length_m = round(math.hypot(dlat * meters_per_lat_deg, dlon * meters_per_lon_deg), 1)
        speed_limit = rng.choice([30, 40, 45, 50, 60])
        for from_node, to_node in ((node_a, node_b), (node_b, node_a)):
            if (from_node, to_node) in seen_pairs:
                continue
            seen_pairs.add((from_node, to_node))
            edges.append(
                {
                    "from_node": from_node,
                    "to_node": to_node,
                    "length_m": length_m,
                    "speed_limit_kmh": speed_limit,
                    "typical_speeds": typical_speeds,
                }
            )

    for row in range(rows):
        for col in range(cols):
            if (row, col) not in node_grid:
                continue
            add_edge((row, col), (row, col + 1))
            add_edge((row, col), (row + 1, col))

    return cameras, edges


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a scaled synthetic camera grid + road graph")
    parser.add_argument("--cameras", type=int, default=300, help="target camera count")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="deterministic RNG seed")
    args = parser.parse_args()

    cameras, edges = generate(args.cameras, args.seed)

    CAMERAS_PATH.write_text(json.dumps(cameras, indent=2) + "\n", encoding="utf-8")
    ROAD_EDGES_PATH.write_text(json.dumps(edges, indent=2) + "\n", encoding="utf-8")

    print(f"[generate_seed] wrote {len(cameras)} cameras -> {CAMERAS_PATH}")
    print(f"[generate_seed] wrote {len(edges)} directed road edges -> {ROAD_EDGES_PATH}")


if __name__ == "__main__":
    main()
