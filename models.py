from enum import Enum, auto
from typing import Optional, List, Tuple
from nodo import Node


class Motorizacao(Enum):
    ELETRICO = auto()
    COMBUSTAO = auto()


class EstadoVeiculo(Enum):
    DISPONIVEL = auto()
    A_CAMINHO_CLIENTE = auto()
    EM_VIAGEM_CLIENTE = auto()
    RECARREGAR = auto()
    INDISPONIVEL = auto()


class Pedido:
    idPedido_counter = 1

    def __init__(
        self,
        origem: Node,
        destino: Node,
        num_passageiros: int,
        prioridade: int = 1,  # (1=baixa, 5=alta)
        pref_ambiental: bool = False,  # (True se prefere elétrico)
    ) -> None:
        self.id_pedido = Pedido.idPedido_counter
        Pedido.idPedido_counter += 1
        self.origem = origem
        self.destino = destino
        self.num_passageiros = num_passageiros
        self.prioridade = prioridade
        self.pref_ambiental = pref_ambiental

    def __repr__(self) -> str:
        return (
            f"Pedido(id={self.id_pedido}, de={self.origem.position}, "
            f"para={self.destino.position}, pax={self.num_passageiros})"
        )

    def __eq__(self, other) -> bool:
        # Dois pedidos são iguais se tiverem o mesmo ID
        if not isinstance(other, Pedido):
            return NotImplemented
        return self.id_pedido == other.id_pedido


class Veiculo:
    def __init__(
        self,
        id_veiculo: str,
        motorizacao: Motorizacao,
        nodo_atual: Node,
        capacidade_passageiros: int,
        custo_por_km: float,
        autonomia_maxima_km: float,
        autonomia_atual_km: float = 0,
        estado: EstadoVeiculo = EstadoVeiculo.DISPONIVEL,
        rota_atribuida: Optional[List[Node]] = None,
        pedido_atual: Optional[Pedido] = None,
    ) -> None:
        self.id_veiculo = id_veiculo
        self.motorizacao = motorizacao
        self.nodo_atual = nodo_atual
        self.capacidade_passageiros = capacidade_passageiros
        self.custo_por_km = custo_por_km
        self.autonomia_maxima_km = autonomia_maxima_km
        self.autonomia_atual_km = autonomia_atual_km
        self.estado = estado

        if self.autonomia_atual_km > self.autonomia_maxima_km:
            self.autonomia_atual_km = self.autonomia_maxima_km

        # Lógica para substituir 'default_factory=list'
        self.rota_atribuida = rota_atribuida if rota_atribuida is not None else []
        self.pedido_atual = pedido_atual

        # A posição (x, y) exata para desenho
        # Começa na posição do seu nó inicial
        self.localizacao_atual_coords: Tuple[float, float] = nodo_atual.position

        # O nó de onde partiu (None se estiver parado)
        self.nodo_origem: Optional[Node] = None
        # O nó para onde vai (None se estiver parado)
        self.nodo_destino: Optional[Node] = None

        # O tempo total em 'minutos' (da aresta) para a viagem
        self.tempo_viagem_total: float = 0.0
        # O tempo em 'minutos' (simulado) que já passou nesta viagem
        self.tempo_viagem_passado: float = 0.0

    def __repr__(self) -> str:
        return (
            f"Veiculo(id={self.id_veiculo}, "
            f"motor={self.motorizacao.name}, "
            f"loc={self.nodo_atual.position}, "
            f"estado={self.estado.name})"
        )

    def __eq__(self, other) -> bool:
        # Dois veículos são iguais se tiverem o mesmo ID
        if not isinstance(other, Veiculo):
            return NotImplemented
        return self.id_veiculo == other.id_veiculo
