import math
import heapq
from typing import List, Optional, Tuple, Dict, TYPE_CHECKING
from collections import deque, defaultdict
from models.node import Node
from graph import CityGraph

if TYPE_CHECKING:
    from models.traffic import TrafficManager


def calculate_time_minutes(dist_km: float, speed_kmh: float) -> float:
    return (dist_km / speed_kmh) * 60.0 if speed_kmh > 0 else float("inf")


def haversine_km(lon_a, lat_a, lon_b, lat_b) -> float:
    """Distância entre dois pontos em km (fórmula de Haversine)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat_a), math.radians(lat_b)
    dphi = math.radians(lat_b - lat_a)
    dlam = math.radians(lon_b - lon_a)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _heuristic_distance(a: Node, b: Node) -> float:
    """Heurística admissível: tempo mínimo assumindo velocidade máxima (120 km/h)."""
    dist = haversine_km(a.position[0], a.position[1], b.position[0], b.position[1])
    return calculate_time_minutes(dist, 120.0)  # 120 km/h


def _reconstruct_path(came_from: Dict[Node, Node], current: Node) -> List[Node]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return list(reversed(path))


def _calc_path_costs(
    path: List[Node],
    graph: CityGraph,
    current_time: float,
    traffic: Optional["TrafficManager"],
) -> Tuple[float, float]:
    """Calcula tempo e distância total de um caminho."""
    total_time, total_dist = 0.0, 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge = graph.connection_weight(u, v)
        if edge:
            dist, time_base, _ = edge
            mult = 1.0
            if traffic:
                mid = ((u.position[0] + v.position[0]) / 2, (u.position[1] + v.position[1]) / 2)
                mult = traffic.get_traffic_factor(mid, current_time)
            total_dist += dist
            total_time += time_base * mult
    return total_time, total_dist


def bfs_route(
    graph: CityGraph,
    start: Node,
    end: Node,
    current_time: float = 0.0,
    traffic: Optional["TrafficManager"] = None,
) -> Optional[Tuple[List[Node], float, float]]:
    """BFS: caminho com menos arestas (não informado)."""
    if start == end:
        return [start], 0.0, 0.0

    queue = deque([start])
    visited = {start}
    came_from: Dict[Node, Node] = {}

    while queue:
        current = queue.popleft()
        if current == end:
            break

        for neighbor in graph.get_node_neighbours(current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                queue.append(neighbor)
                if neighbor == end:
                    break
        else:
            continue
        break

    if end not in came_from:
        return None

    path = _reconstruct_path(came_from, end)
    time, dist = _calc_path_costs(path, graph, current_time, traffic)
    return path, time, dist


def greedy_route(
    graph: CityGraph,
    start: Node,
    end: Node,
    current_time: float = 0.0,
    traffic: Optional["TrafficManager"] = None,
) -> Optional[Tuple[List[Node], float, float]]:
    """Greedy: segue sempre o nó mais próximo do destino (informado)."""
    heap = [(_heuristic_distance(start, end), id(start), start)]
    came_from: Dict[Node, Node] = {}
    visited = {start}

    while heap:
        _, _, current = heapq.heappop(heap)

        if current == end:
            path = _reconstruct_path(came_from, current)
            time, dist = _calc_path_costs(path, graph, current_time, traffic)
            return path, time, dist

        for neighbor in graph.get_node_neighbours(current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                heapq.heappush(heap, (_heuristic_distance(neighbor, end), id(neighbor), neighbor))

    return None


def astar_route(
    graph: CityGraph,
    start: Node,
    end: Node,
    current_time: float = 0.0,
    traffic: Optional["TrafficManager"] = None,
) -> Optional[Tuple[List[Node], float, float]]:
    """A*: caminho óptimo com f(n) = g(n) + h(n)."""
    heap = [(0, id(start), start)]
    in_heap = {start}

    came_from: Dict[Node, Node] = {}
    g_score: Dict[Node, float] = defaultdict(lambda: float("inf"))
    d_score: Dict[Node, float] = defaultdict(lambda: float("inf"))
    g_score[start] = 0.0
    d_score[start] = 0.0

    closed = set()

    while heap:
        _, _, current = heapq.heappop(heap)
        in_heap.discard(current)

        if current == end:
            path = _reconstruct_path(came_from, current)
            return path, g_score[current], d_score[current]

        closed.add(current)

        for neighbor in graph.get_node_neighbours(current):
            if neighbor in closed:
                continue

            edge = graph.connection_weight(current, neighbor)
            if not edge:
                continue

            dist, time_base, _ = edge
            mult = 1.0
            if traffic:
                mid = ((current.position[0] + neighbor.position[0]) / 2,
                       (current.position[1] + neighbor.position[1]) / 2)
                mult = traffic.get_traffic_factor(mid, current_time)

            tentative_g = g_score[current] + time_base * mult

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                d_score[neighbor] = d_score[current] + dist
                f = tentative_g + _heuristic_distance(neighbor, end)

                if neighbor not in in_heap:
                    heapq.heappush(heap, (f, id(neighbor), neighbor))
                    in_heap.add(neighbor)

    return None


def find_route(
    algorithm: str,
    graph: CityGraph,
    start: Node,
    end: Node,
    current_time: float = 0.0,
    traffic_manager: Optional["TrafficManager"] = None,
) -> Optional[Tuple[List[Node], float, float]]:
    """Executa algoritmo de rota (astar, bfs, greedy)."""
    algo = algorithm.lower()
    if algo == "bfs":
        return bfs_route(graph, start, end, current_time, traffic_manager)
    elif algo == "greedy":
        return greedy_route(graph, start, end, current_time, traffic_manager)
    else:
        return astar_route(graph, start, end, current_time, traffic_manager)
