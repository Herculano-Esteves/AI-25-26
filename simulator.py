import math
from mapGen import criar_mapa_gerado, criar_pedido_aleatorio
from search import procurar_rota_a_star
from models import EstadoVeiculo, Veiculo, Pedido, Node
from typing import List


def _peso_de_distancia(a: Node, b: Node) -> float:
    (x1, y1) = a.position
    (x2, y2) = b.position
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


class Simulador:
    # Simulation Constants
    LARGURA_MAPA = 20
    ALTURA_MAPA = 20
    SIM_TEMPO_POR_TICK = 0.1  # Time in minutes per frame
    # Lowest autonomy threshold
    LIMITE_AUTONOMIA_BAIXA = 50.0

    def __init__(self):
        # Variables
        self.mapa = None
        self.veiculos: List[Veiculo] = []
        self.pedidos: List[Pedido] = []
        self.pedidos_a_ir_buscar: List[Pedido] = []
        self.pedidos_destinos: List[Pedido] = []

        # Setup
        self.configurar_novo_mapa()

    def configurar_novo_mapa(self):
        print("A criar novo mapa...")
        self.mapa, self.veiculos, self.pedidos = criar_mapa_gerado(
            self.LARGURA_MAPA, self.ALTURA_MAPA, 0.02, 0.005
        )
        self.pedidos_a_ir_buscar = []
        self.pedidos_destinos = []

    def passo_simulacao(self):
        tempo_a_avancar = self.SIM_TEMPO_POR_TICK
        for v in self.veiculos:
            self._gerir_veiculo(v, tempo_a_avancar)
        self._atribuir_pedidos_pendentes()
        self._gerar_novos_pedidos_se_necessario()

    def _gerir_veiculo(self, v: Veiculo, tempo_a_avancar: float):
        self._atualizar_movimento_veiculo(v, tempo_a_avancar)

        if not v.nodo_destino:
            self._gerir_veiculo_parado(v)

    def _atualizar_movimento_veiculo(self, v: Veiculo, tempo_a_avancar: float):
        if not v.nodo_destino:
            return

        v.tempo_viagem_passado += tempo_a_avancar

        if v.tempo_viagem_passado >= v.tempo_viagem_total:
            v.autonomia_atual_km -= v.distancia_viagem_total

            v.nodo_atual = v.nodo_destino
            v.localizacao_atual_coords = v.nodo_atual.position

            v.nodo_origem = None
            v.nodo_destino = None
            v.tempo_viagem_passado = 0
            v.tempo_viagem_total = 0
            v.distancia_viagem_total = 0.0

        else:
            progresso = v.tempo_viagem_passado / v.tempo_viagem_total
            x1, y1 = v.nodo_origem.position
            x2, y2 = v.nodo_destino.position
            novo_x = x1 + (x2 - x1) * progresso
            novo_y = y1 + (y2 - y1) * progresso
            v.localizacao_atual_coords = (novo_x, novo_y)

    def _gerir_veiculo_parado(self, v: Veiculo):
        if v.rota_atribuida:
            if v.rota_atribuida[0] != v.nodo_atual:
                v.rota_atribuida = []

            elif len(v.rota_atribuida) >= 2:
                proximo_no = v.rota_atribuida[1]
                v.nodo_origem = v.nodo_atual
                v.nodo_destino = proximo_no
                v.rota_atribuida = v.rota_atribuida[1:]

                aresta_info = self.mapa.obter_peso_aresta(v.nodo_origem, v.nodo_destino)
                if aresta_info:
                    distancia, tempo = aresta_info
                    v.distancia_viagem_total = distancia
                    v.tempo_viagem_total = tempo
                    v.tempo_viagem_passado = 0.0
                return

            else:
                v.rota_atribuida = []

        if v.estado == EstadoVeiculo.A_CAMINHO_CLIENTE:
            self._gerir_estado_a_caminho(v)

        elif v.estado == EstadoVeiculo.EM_VIAGEM_CLIENTE:
            self._gerir_estado_em_viagem(v)

        elif v.estado == EstadoVeiculo.DISPONIVEL:
            # Verificar se precisa de reabastecer
            pass

    def _gerir_estado_a_caminho(self, v: Veiculo):
        print(
            f"{v.id_veiculo} em {v.nodo_atual.position}. A iniciar viagem para {v.pedido_atual.destino.position}"
        )

        self.pedidos_a_ir_buscar.remove(v.pedido_atual)
        self.pedidos_destinos.append(v.pedido_atual)
        v.estado = EstadoVeiculo.EM_VIAGEM_CLIENTE

        caminho = procurar_rota_a_star(self.mapa, v.nodo_atual, v.pedido_atual.destino)
        v.rota_atribuida = caminho if caminho else []

    def _gerir_estado_em_viagem(self, v: Veiculo):
        print(
            f"{v.id_veiculo} completou a viagem em {v.nodo_atual.position}. Disponível."
            f"Autonomia restante: {v.autonomia_atual_km:.1f} km"
        )
        self.pedidos_destinos.remove(v.pedido_atual)
        v.estado = EstadoVeiculo.DISPONIVEL
        v.pedido_atual = None
        v.rota_atribuida = []

    def _atribuir_pedidos_pendentes(self):
        if not self.pedidos:
            return

        veiculos_disponiveis = [
            v for v in self.veiculos if v.estado == EstadoVeiculo.DISPONIVEL
        ]

        if not veiculos_disponiveis:
            return

        # Goes through a copy of the list to allow removal
        for pedido in self.pedidos[:]:

            best_vehicle = None
            lowest_weight = float("inf")

            for v in veiculos_disponiveis:
                weight = _peso_de_distancia(v.nodo_atual, pedido.origem)
                if weight < lowest_weight:
                    lowest_weight = weight
                    best_vehicle = v

            if best_vehicle:
                self.pedidos.remove(pedido)
                veiculos_disponiveis.remove(best_vehicle)
                self._atribuir_pedido_a_veiculo(pedido, best_vehicle)

                if not veiculos_disponiveis:
                    break

    def _atribuir_pedido_a_veiculo(self, pedido: Pedido, v: Veiculo):
        self.pedidos_a_ir_buscar.append(pedido)
        v.pedido_atual = pedido
        v.estado = EstadoVeiculo.A_CAMINHO_CLIENTE

        print(
            f"[Atribuição] {v.id_veiculo} (mais próximo) aceitou {pedido.id_pedido}. "
            f"A caminho de {pedido.origem.position}"
        )

        caminho = procurar_rota_a_star(self.mapa, v.nodo_atual, pedido.origem)
        v.rota_atribuida = caminho if caminho else []

    def _gerar_novos_pedidos_se_necessario(self):
        if not self.pedidos:
            print("[Simulação] Fila de pedidos vazia. A gerar 4 novos pedidos.")
            for _ in range(4):
                self.pedidos.append(criar_pedido_aleatorio(list(self.mapa.nos)))
