from mapGen import criar_mapa_gerado, criar_pedido_aleatorio
from search import procurar_rota_a_star
from models import EstadoVeiculo


class Simulador:
    # Simulation Constants
    LARGURA_MAPA = 20
    ALTURA_MAPA = 20
    SIM_TEMPO_POR_TICK = 0.1  # Time in minutes per frame

    def __init__(self):
        # Variables
        self.mapa = None
        self.veiculos = []
        self.pedidos = []
        self.pedidos_a_ir_buscar = []
        self.pedidos_destinos = []

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
            # In movement
            if v.nodo_destino:
                v.tempo_viagem_passado += tempo_a_avancar

                if v.tempo_viagem_passado >= v.tempo_viagem_total:
                    # Arrived at destination
                    v.nodo_atual = v.nodo_destino
                    v.nodo_origem = None
                    v.nodo_destino = None
                    v.tempo_viagem_passado = 0
                    v.localizacao_atual_coords = v.nodo_atual.position

                else:
                    # On the way
                    progresso = v.tempo_viagem_passado / v.tempo_viagem_total
                    x1, y1 = v.nodo_origem.position
                    x2, y2 = v.nodo_destino.position
                    novo_x = x1 + (x2 - x1) * progresso
                    novo_y = y1 + (y2 - y1) * progresso
                    v.localizacao_atual_coords = (novo_x, novo_y)
                    continue  # Skips to next vehicle

            # With route assigned but stopped
            if v.rota_atribuida:
                if v.rota_atribuida[0] != v.nodo_atual:
                    v.rota_atribuida = []  # Invalid route

                elif len(v.rota_atribuida) >= 2:
                    # Will start moving to next node
                    proximo_no = v.rota_atribuida[1]
                    v.nodo_origem = v.nodo_atual
                    v.nodo_destino = proximo_no
                    v.rota_atribuida = v.rota_atribuida[1:]

                    aresta_info = self.mapa.obter_peso_aresta(
                        v.nodo_origem, v.nodo_destino
                    )
                    if aresta_info:
                        distancia, tempo = aresta_info
                        v.tempo_viagem_total = tempo
                        v.tempo_viagem_passado = 0.0
                    continue  # Skips to next vehicle

                else:
                    v.rota_atribuida = []  # Reached destination of route

            # If here there is no movement or route
            if v.estado == EstadoVeiculo.DISPONIVEL:
                if not self.pedidos:
                    for _ in range(4):
                        self.pedidos.append(criar_pedido_aleatorio(list(self.mapa.nos)))
                    continue  # No requests available

                # First request in the list
                pedido_escolhido = self.pedidos.pop(0)
                self.pedidos_a_ir_buscar.append(pedido_escolhido)

                v.pedido_atual = pedido_escolhido
                v.estado = EstadoVeiculo.A_CAMINHO_CLIENTE
                print(
                    f"{v.id_veiculo} aceitou {pedido_escolhido.id_pedido}. A caminho de {pedido_escolhido.origem.position}"
                )

                caminho = procurar_rota_a_star(
                    self.mapa, v.nodo_atual, pedido_escolhido.origem
                )
                v.rota_atribuida = caminho if caminho else []

            elif v.estado == EstadoVeiculo.A_CAMINHO_CLIENTE:
                # Reached client
                print(
                    f"{v.id_veiculo} em {v.nodo_atual.position}. A iniciar viagem para {v.pedido_atual.destino.position}"
                )

                self.pedidos_a_ir_buscar.remove(v.pedido_atual)
                self.pedidos_destinos.append(v.pedido_atual)

                v.estado = EstadoVeiculo.EM_VIAGEM_CLIENTE

                caminho = procurar_rota_a_star(
                    self.mapa, v.nodo_atual, v.pedido_atual.destino
                )
                v.rota_atribuida = caminho if caminho else []

            elif v.estado == EstadoVeiculo.EM_VIAGEM_CLIENTE:
                # Just dropped off the client
                print(
                    f"{v.id_veiculo} completou a viagem em {v.nodo_atual.position}. Disponível."
                )

                self.pedidos_destinos.remove(v.pedido_atual)
                v.estado = EstadoVeiculo.DISPONIVEL
                v.pedido_atual = None
                v.rota_atribuida = []
