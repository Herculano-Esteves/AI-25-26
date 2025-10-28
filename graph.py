from typing import Tuple, Set, Dict, List, Optional
from nodo import Node

# (distancia_km, tempo_minutos)
TipoAresta = Tuple[float, float]


class GrafoCidade:
    """
    Formato: self.adj = {
        Node_A: {Node_B: (dist, tempo), Node_C: (dist, tempo)},
        Node_B: {Node_A: (dist, tempo)}
    }
    """

    def __init__(self):
        # Armazena todos os objetos Node únicos
        self.nos: Set[Node] = set()

        # O mapa de adjacência (usa Node como chave)
        self.adj: Dict[Node, Dict[Node, TipoAresta]] = {}

        # Posição -> Nó O(1)
        self.posicao_para_no: Dict[Tuple[int, int], Node] = {}

    def adicionar_no(self, no: Node):
        """
        Adiciona um nó (Node) ao grafo.
        Se um nó com a mesma posição já existir substitui.
        """
        if no not in self.nos:
            self.nos.add(no)
            self.adj[no] = {}  # Inicializa o dicionário de vizinhos
            self.posicao_para_no[no.position] = no  # Adiciona ao índice

    def existe_no(self, no: Node) -> bool:
        return no in self.nos

    def obter_no_por_posicao(self, position: Tuple[int, int]) -> Optional[Node]:
        return self.posicao_para_no.get(position)

    def adicionar_aresta(
        self,
        origem: Node,
        destino: Node,
        distancia_km: float,
        tempo_minutos: float,
        bidirecional: bool = True,
    ):
        """
        Adiciona uma aresta (caminho) entre dois Nós.
        Se os nós não existirem no grafo, são adicionados.
        """
        # Garante que os nós existem no grafo
        self.adicionar_no(origem)
        self.adicionar_no(destino)

        # Adiciona a aresta origem -> destino
        self.adj[origem][destino] = (distancia_km, tempo_minutos)

        if bidirecional:
            # Adiciona a aresta destino -> origem
            self.adj[destino][origem] = (distancia_km, tempo_minutos)

    def obter_vizinhos(self, no: Node) -> List[Node]:
        if no not in self.adj:
            return []
        return list(self.adj[no].keys())

    def obter_peso_aresta(self, origem: Node, destino: Node) -> Optional[TipoAresta]:
        """
        Retorna o peso (distancia, tempo) de uma aresta.
        Retorna None se o caminho não existir.
        """
        if origem in self.adj and destino in self.adj[origem]:
            return self.adj[origem][destino]
        return None

    def __str__(self) -> str:
        # Método auxiliar para imprimir o grafo de forma legível
        output = "Grafo da Cidade:\n"
        output += f"Total de Nós: {len(self.nos)}\n"
        output += "--- Arestas ---\n"

        if not self.adj:
            return output + "(Grafo vazio)"

        for no, vizinhos in self.adj.items():
            output += f"  {no}:\n"
            if not vizinhos:
                output += "    -> (Nenhum vizinho)\n"
            for vizinho, peso in vizinhos.items():
                dist, tempo = peso
                output += f"    -> {vizinho} | (Dist: {dist} km, Tempo: {tempo} min)\n"
        return output