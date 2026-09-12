from collections import defaultdict
from heapq import heappop, heappush
from math import radians, cos, sin, asin, sqrt


def haversine_km(lat1, lon1, lat2, lon2):
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _speed_for_bucket(typical_speeds: dict, hour: int) -> float:
    buckets = sorted((int(k), float(v)) for k, v in typical_speeds.items())
    speed = buckets[0][1]
    for bucket, value in buckets:
        if hour >= bucket:
            speed = value
    return max(speed, 5.0)


def astar_path(edges: list[dict], nodes: dict, start: str, goal: str, hour_bucket: int):
    graph = defaultdict(list)
    for e in edges:
        speed = _speed_for_bucket(e["typical_speeds"], hour_bucket)
        weight = e["length_m"] / (speed * (1000 / 3600))
        graph[e["from_node"]].append((e["to_node"], weight))

    open_set = [(0, start)]
    g = {start: 0}
    came = {}

    while open_set:
        _, current = heappop(open_set)
        if current == goal:
            break
        for nxt, w in graph[current]:
            tentative = g[current] + w
            if tentative < g.get(nxt, float("inf")):
                came[nxt] = current
                g[nxt] = tentative
                hn = haversine_km(nodes[nxt]["lat"], nodes[nxt]["lon"], nodes[goal]["lat"], nodes[goal]["lon"])
                heappush(open_set, (tentative + hn, nxt))

    if goal not in g:
        return []

    path_nodes = [goal]
    while path_nodes[-1] != start:
        path_nodes.append(came[path_nodes[-1]])
    path_nodes.reverse()
    return [[nodes[n]["lat"], nodes[n]["lon"]] for n in path_nodes]
