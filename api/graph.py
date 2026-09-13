"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Small A* over the seeded road_edges graph, per TEAM.md §4.4/§8. Weight =
length_m / typical_speed[hour] (m/s), so shortest-time path, not shortest
distance. ~6 nodes, ~14 directed edges — a plain dict-of-lists graph is
entirely sufficient at this scale.
"""
import heapq
import math
from typing import Optional


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))


def astar_path(
    edges: list[dict],
    node_coords: dict[str, tuple[float, float]],
    start: str,
    goal: str,
    hour: int,
) -> Optional[list[str]]:
    """Returns the node sequence start..goal minimizing implied travel time,
    or None if unreachable. `edges` rows: from_node, to_node, length_m,
    typical_speeds (dict[str(hour) -> kmh])."""
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for e in edges:
        speed_kmh = e["typical_speeds"].get(str(hour), e["speed_limit_kmh"])
        weight_sec = e["length_m"] / 1000 / max(speed_kmh, 1) * 3600
        adjacency.setdefault(e["from_node"], []).append((e["to_node"], weight_sec))

    def heuristic(node: str) -> float:
        if node not in node_coords or goal not in node_coords:
            return 0.0
        # Optimistic: distance / a generous free-flow speed (60 km/h).
        return _haversine_km(node_coords[node], node_coords[goal]) / 60 * 3600

    open_set = [(heuristic(start), 0.0, start, [start])]
    best_cost: dict[str, float] = {start: 0.0}

    while open_set:
        _, cost_so_far, node, path = heapq.heappop(open_set)
        if node == goal:
            return path
        if cost_so_far > best_cost.get(node, math.inf):
            continue
        for neighbor, weight in adjacency.get(node, []):
            new_cost = cost_so_far + weight
            if new_cost < best_cost.get(neighbor, math.inf):
                best_cost[neighbor] = new_cost
                heapq.heappush(open_set, (new_cost + heuristic(neighbor), new_cost, neighbor, path + [neighbor]))

    return None
