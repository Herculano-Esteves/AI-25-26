#!/usr/bin/env python3
"""
Benchmark dos algoritmos de procura de caminho.
Gera dados para a tabela do relatório.
"""
import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapGen import generate_map
from Simulation.search_algorithms import bfs_route, greedy_route, astar_route

def bfs_with_stats(graph, start, end):
    """BFS que retorna também nós visitados."""
    from collections import deque
    
    if start == end:
        return [start], 0.0, 0.0, 1
    
    queue = deque([start])
    visited = {start}
    came_from = {}
    
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
        return None, 0.0, 0.0, len(visited)
    
    path = [end]
    current = end
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path = list(reversed(path))
    
    total_time, total_dist = 0.0, 0.0
    for i in range(len(path) - 1):
        edge = graph.connection_weight(path[i], path[i + 1])
        if edge:
            total_dist += edge[0]
            total_time += edge[1]
    
    return path, total_time, total_dist, len(visited)


def greedy_with_stats(graph, start, end):
    """Greedy que retorna também nós visitados."""
    import heapq
    from Simulation.search_algorithms import _heuristic_distance, _calc_path_costs, _reconstruct_path
    
    if start == end:
        return [start], 0.0, 0.0, 1
    
    heap = [(_heuristic_distance(start, end), id(start), start)]
    came_from = {}
    visited = {start}
    
    while heap:
        _, _, current = heapq.heappop(heap)
        
        if current == end:
            path = _reconstruct_path(came_from, current)
            time, dist = _calc_path_costs(path, graph, 0.0, None)
            return path, time, dist, len(visited)
        
        for neighbor in graph.get_node_neighbours(current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                heapq.heappush(heap, (_heuristic_distance(neighbor, end), id(neighbor), neighbor))
    
    return None, 0.0, 0.0, len(visited)


def astar_with_stats(graph, start, end):
    """A* que retorna também nós visitados."""
    import heapq
    from collections import defaultdict
    from Simulation.search_algorithms import _heuristic_distance, _reconstruct_path
    
    if start == end:
        return [start], 0.0, 0.0, 1
    
    heap = [(0, id(start), start)]
    in_heap = {start}
    
    came_from = {}
    g_score = defaultdict(lambda: float("inf"))
    d_score = defaultdict(lambda: float("inf"))
    g_score[start] = 0.0
    d_score[start] = 0.0
    
    closed = set()
    
    while heap:
        _, _, current = heapq.heappop(heap)
        in_heap.discard(current)
        
        if current == end:
            path = _reconstruct_path(came_from, current)
            return path, g_score[current], d_score[current], len(closed) + len(in_heap)
        
        closed.add(current)
        
        for neighbor in graph.get_node_neighbours(current):
            if neighbor in closed:
                continue
            
            edge = graph.connection_weight(current, neighbor)
            if not edge:
                continue
            
            dist, time_base, _ = edge
            tentative_g = g_score[current] + time_base
            
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                d_score[neighbor] = d_score[current] + dist
                f = tentative_g + _heuristic_distance(neighbor, end)  
                
                if neighbor not in in_heap:
                    heapq.heappush(heap, (f, id(neighbor), neighbor))
                    in_heap.add(neighbor)
    
    return None, 0.0, 0.0, len(closed)


def run_benchmark(num_tests=100, seed=42):
    """Executa benchmark e retorna estatísticas."""
    print("A carregar mapa de Braga...")
    graph = generate_map()
    nodes = list(graph.nos)
    
    print(f"Mapa carregado: {len(nodes)} nós")
    print(f"A executar {num_tests} testes...")
    
    rng = random.Random(seed)
    
    results = {
        "BFS": {"time_ms": 0.0, "cost_min": 0.0, "path_nodes": 0, "visited": 0, "success": 0},
        "Greedy": {"time_ms": 0.0, "cost_min": 0.0, "path_nodes": 0, "visited": 0, "success": 0},
        "A*": {"time_ms": 0.0, "cost_min": 0.0, "path_nodes": 0, "visited": 0, "success": 0},
    }
    
    algorithms = [
        ("BFS", bfs_with_stats),
        ("Greedy", greedy_with_stats),
        ("A*", astar_with_stats),
    ]
    
    for i in range(num_tests):
        start = rng.choice(nodes)
        end = rng.choice(nodes)
        while end == start:
            end = rng.choice(nodes)
        
        for name, func in algorithms:
            t0 = time.perf_counter()
            path, cost, dist, visited = func(graph, start, end)
            t1 = time.perf_counter()
            
            if path:
                results[name]["time_ms"] += (t1 - t0) * 1000
                results[name]["cost_min"] += cost
                results[name]["path_nodes"] += len(path)
                results[name]["visited"] += visited
                results[name]["success"] += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Progresso: {i + 1}/{num_tests}")
    
    return results


def format_results(results):
    """Formata resultados para a tabela do relatório."""
    print("\n" + "=" * 70)
    print("RESULTADOS PARA O RELATÓRIO")
    print("=" * 70)
    
    print("\nTabela Typst (copiar para report_template.typ):")
    print("-" * 70)
    
    print("""#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 3 { luma(235) } else { white },
    [*Algoritmo*], [*Σ Tempo (ms)*], [*Σ Custo (min)*], [*Σ Nós Solução*], [*Σ Nós Visitados*],""")
    
    for name in ["BFS", "Greedy", "A*"]:
        r = results[name]
        print(f"    [{name}], [{r['time_ms']:.1f}], [{r['cost_min']:.1f}], [{r['path_nodes']}], [{r['visited']}],")
    
    print("""  ),
  caption: [Somas das Métricas de Procura (100 rotas de teste)],
) <tab:search-comparison>""")
    
    print("\n" + "-" * 70)
    print("\nResumo:")
    for name, r in results.items():
        print(f"  {name}: {r['success']} rotas encontradas, "
              f"tempo médio {r['time_ms']/max(r['success'],1):.2f}ms, "
              f"custo médio {r['cost_min']/max(r['success'],1):.2f}min")


if __name__ == "__main__":
    results = run_benchmark(num_tests=100, seed=42)
    format_results(results)
