import heapq
import math
from typing import List, Optional, Dict, Tuple, Set, Generator
from dataclasses import dataclass

from nodo import Node
from graph import GrafoCidade


# Funções Auxiliares do A*


def _distancia_heuristica(a: Node, b: Node) -> float:
    (x1, y1) = a.position
    (x2, y2) = b.position
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _reconstruir_caminho(came_from: Dict[Node, Node], current: Node) -> List[Node]:
    caminho_total = [current]
    while current in came_from:
        current = came_from[current]
        caminho_total.append(current)
    return list(reversed(caminho_total))


# Implementação A*


def procurar_rota_a_star(
    mapa: GrafoCidade, inicio: Node, fim: Node
) -> Optional[List[Node]]:
    closed_set: Set[Node] = set()
    open_set = []
    heapq.heappush(open_set, (0, hash(inicio), inicio))
    open_set_map = {inicio}

    # came_from: Dicionário para reconstruir o caminho.
    came_from: Dict[Node, Node] = {}

    # Inicializa todos os custos a infinito.
    g_score: Dict[Node, float] = {no: float("inf") for no in mapa.nos}
    g_score[inicio] = 0.0

    # f_score: Custo total estimado (g + h) do início ao fim, passando por 'n'.
    f_score: Dict[Node, float] = {no: float("inf") for no in mapa.nos}
    f_score[inicio] = _distancia_heuristica(inicio, fim)  # f do início = h

    while open_set:

        # Obtém o nó da priority queue com o menor f_score
        current_f, _, current = heapq.heappop(open_set)
        open_set_map.remove(current)

        # Fim
        if current == fim:
            # Encontrámos o caminho! Reconstrói-o e retorna.
            return _reconstruir_caminho(came_from, current)

        # Adiciona o nó atual ao set de explorados
        closed_set.add(current)

        # Explorar Vizinhos
        for vizinho in mapa.obter_vizinhos(current):
            # Ignora vizinhos já explorados
            if vizinho in closed_set:
                continue

            # Obtém o peso da aresta (distância, tempo)
            aresta = mapa.obter_peso_aresta(current, vizinho)
            if aresta is None:
                continue

            # A* otimiza pelo *tempo* (índice 1)
            distancia_aresta, tempo_aresta = aresta

            # Calcula o custo 'g'
            tentative_g_score = (
                g_score[current] + tempo_aresta + distancia_aresta
            )  # melhorar depois o custo

            # Verificar se este é um caminho melhor
            if tentative_g_score < g_score[vizinho]:
                came_from[vizinho] = current
                g_score[vizinho] = tentative_g_score
                f_score[vizinho] = tentative_g_score + _distancia_heuristica(
                    vizinho, fim
                )

                if vizinho not in open_set_map:
                    heapq.heappush(open_set, (f_score[vizinho], hash(vizinho), vizinho))
                    open_set_map.add(vizinho)
    # Sem caminho
    return None
