import networkx as nx
import matplotlib.pyplot as plt
from graph import GrafoCidade
from nodo import Node
from models import Veiculo, Pedido, Motorizacao, EstadoVeiculo

def desenhar_grafo_com_elementos(grafo: GrafoCidade, veiculos, pedidos, filename="grafo_cidade.png"):
    G = nx.DiGraph()

    # Adiciona nós e arestas
    for no in grafo.nos:
        G.add_node(no, pos=no.position)

    for origem, vizinhos in grafo.adj.items():
        for destino, (dist, tempo) in vizinhos.items():
            G.add_edge(origem, destino, dist=dist, tempo=tempo)

    pos = {no: no.position for no in grafo.nos}

    plt.figure(figsize=(15, 15))

    # --- Desenha arestas ---
    nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, alpha=0.5)

    # --- Diferenciar tipos de nós ---
    postos_gas = [n for n in grafo.nos if n.gas_pumps > 0]
    estacoes_ev = [n for n in grafo.nos if n.energy_chargers > 0]
    normais = [n for n in grafo.nos if n not in postos_gas + estacoes_ev]

    nx.draw_networkx_nodes(G, pos, nodelist=normais, node_color="lightblue", node_size=600, label="Nó normal")
    nx.draw_networkx_nodes(G, pos, nodelist=postos_gas, node_color="orange", node_shape="s", node_size=800, label="Posto Gasolina")
    nx.draw_networkx_nodes(G, pos, nodelist=estacoes_ev, node_color="limegreen", node_shape="D", node_size=800, label="Estação Elétrica")

    # --- Desenha veículos ---
    
    labels_veiculos_adicionados = set()
    
    for v in veiculos:
        cor = "green" if v.motorizacao == Motorizacao.ELETRICO else "red"
        
        label_veiculo = f"Veículo {v.motorizacao.name}"
        if label_veiculo in labels_veiculos_adicionados:
            label_veiculo = "" 
        else:
            labels_veiculos_adicionados.add(label_veiculo) 

        plt.scatter(
            v.localizacao_atual.position[0],
            v.localizacao_atual.position[1],
            color=cor,
            s=200,
            marker="^",
            edgecolors="black",
            label=label_veiculo,
            zorder=3
        )

    # --- Desenha pedidos (origem) ---
    label_pedido_adicionado = False
    
    for p in pedidos:
        
        label_pedido = ""
        if not label_pedido_adicionado:
            label_pedido = "Origem Pedido"
            label_pedido_adicionado = True

        plt.scatter(
            p.origem.position[0],
            p.origem.position[1],
            color="blue",
            s=150,
            marker="*",
            edgecolors="black",
            label=label_pedido,
            zorder=3
        )

    nx.draw_networkx_labels(G, pos, {n: str(n.position) for n in grafo.nos}, font_size=9)

    plt.legend()
    plt.title("Mapa da Cidade - Veículos, Pedidos e Infraestrutura")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(filename, dpi=200)
    plt.close()
    print(f"✅ Mapa salvo em '{filename}'")