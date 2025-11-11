import heapq
import math
from typing import List, Optional, Dict, Set, Tuple

from models.node import Node
from graph import CityGraph


# A* Helper Functions


def _heuristic_distance(a: Node, b: Node) -> float:
    (lon1, lat1) = a.position
    (lon2, lat2) = b.position

    # haversine formula
    def haversine_km(lon_a, lat_a, lon_b, lat_b):
        R = 6371.0  # Earth radius
        phi1 = math.radians(lat_a)
        phi2 = math.radians(lat_b)
        dphi = math.radians(lat_b - lat_a)
        dlambda = math.radians(lon_b - lon_a)
        sa = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(sa), math.sqrt(1 - sa))
        return R * c

    distance_km = haversine_km(lon1, lat1, lon2, lat2)
    # heuristic in minutes: average speed 30 km/h
    # minutes = km / (km/h) * 60
    avg_speed_kmh = 30.0
    return (distance_km / avg_speed_kmh) * 60.0


def _reconstruct_path(came_from: Dict[Node, Node], current: Node) -> List[Node]:
    total_path = [current]
    while current in came_from:
        current = came_from[current]
        total_path.append(current)
    return list(reversed(total_path))


# A* Implementation


def find_a_star_route(
    map: CityGraph, start_node: Node, end_node: Node
) -> Optional[Tuple[List[Node], float, float]]:
    # returns (path, total_time, total_distance)
    closed_set: Set[Node] = set()
    open_set = []
    heapq.heappush(open_set, (0, hash(start_node), start_node))
    open_set_map = {start_node}

    # came_from: Dictionary to reconstruct the path.
    came_from: Dict[Node, Node] = {}

    # g_score: Cost (time) from start to 'n'
    g_score: Dict[Node, float] = {no: float("inf") for no in map.nos}
    g_score[start_node] = 0.0

    # d_score: Distance (km) from start to 'n' (following the fastest path)
    d_score: Dict[Node, float] = {no: float("inf") for no in map.nos}
    d_score[start_node] = 0.0

    # f_score: Estimated total cost (g + h) from start to end, passing through 'n'.
    f_score: Dict[Node, float] = {no: float("inf") for no in map.nos}
    f_score[start_node] = _heuristic_distance(start_node, end_node)

    while open_set:

        # Get the node from the priority queue with the lowest f_score
        current_f, _, current = heapq.heappop(open_set)
        open_set_map.remove(current)

        # End
        if current == end_node:
            path = _reconstruct_path(came_from, current)
            total_time = g_score[current]
            total_distance = d_score[current]
            return path, total_time, total_distance

        closed_set.add(current)

        # Explore Neighbors
        for neighbor in map.get_node_neighbours(current):
            # Ignore neighbors already explored
            if neighbor in closed_set:
                continue

            # Get the edge weight (distance, time)
            edge_info = map.connection_weight(current, neighbor)
            if edge_info is None:
                continue

            # A* optimizes by *time* (index 1)
            edge_distance, edge_time = edge_info

            # Calculate the 'g' cost (time)
            tentative_g_score = g_score[current] + edge_time

            # Check if this is a better path (in terms of time)
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                # Also update the distance for this new fastest path
                d_score[neighbor] = d_score[current] + edge_distance

                f_score[neighbor] = tentative_g_score + _heuristic_distance(neighbor, end_node)

                if neighbor not in open_set_map:
                    heapq.heappush(open_set, (f_score[neighbor], hash(neighbor), neighbor))
                    open_set_map.add(neighbor)
    # No path found
    return None
