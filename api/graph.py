def guess_route(start_node: str, end_node: str) -> list:
    # MVP Hardcoded Adjacency for the Z1/Z2 zones in seed.sql
    # In a production app, query road_edges for A* pathfinding.
    graph = {
        "N1": ["N2"],
        "N2": ["N1", "N3"],
        "N3": ["N2", "N4"],
        "N4": ["N3", "N5"],
        "N5": ["N4", "N6"],
        "N6": ["N5"]
    }
    
    # Simple Breadth-First Search for the MVP
    queue = [[start_node]]
    visited = set()
    
    while queue:
        path = queue.pop(0)
        node = path[-1]
        
        if node == end_node:
            return path
            
        if node not in visited:
            for adjacent in graph.get(node, []):
                new_path = list(path)
                new_path.append(adjacent)
                queue.append(new_path)
            visited.add(node)
            
    return [] # No path found