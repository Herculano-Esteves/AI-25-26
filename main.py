from graph import GrafoCidade
from nodo import Node
from models import Veiculo, Pedido, Motorizacao
from grafo_png import desenhar_grafo_com_elementos


def criar_mapa_exemplo():
    """Cria um grafo exemplo para testes."""
    centro = Node(position=(0, 0))
    zona_norte = Node(position=(0, 50))
    zona_sul = Node(position=(0, -50))
    estacao_carga = Node(position=(100, 100), energy_chargers=4)
    posto_gasolina = Node(position=(-10, -10), gas_pumps=2)
    aeroporto = Node(position=(10, 10))
    porto = Node(position=(50, 70))

    mapa = GrafoCidade()
    mapa.adicionar_aresta(centro, zona_norte, 5.0, 10.0)
    mapa.adicionar_aresta(centro, zona_sul, 5.2, 11.0)
    mapa.adicionar_aresta(centro, estacao_carga, 1.5, 5.0)
    mapa.adicionar_aresta(centro, posto_gasolina, 1.6, 6.0)
    mapa.adicionar_aresta(centro, porto, 1.6, 6.0)
    mapa.adicionar_aresta(aeroporto, centro, 15.0, 25.0, bidirecional=False)

    veiculos = [
        Veiculo("V1", Motorizacao.ELETRICO, estacao_carga, 4, 0.2, 250),
        Veiculo("V2", Motorizacao.COMBUSTAO, posto_gasolina, 4, 0.3, 400),
        Veiculo("V3", Motorizacao.COMBUSTAO, centro, 4, 0.3, 400),
    ]

    pedidos = [
        Pedido(1, origem=zona_norte, destino=aeroporto, num_passageiros=2),
        Pedido(2, origem=zona_sul, destino=centro, num_passageiros=1),
    ]

    return mapa, veiculos, pedidos


def main():
    mapa, veiculos, pedidos = criar_mapa_exemplo()
    opcao = -1

    while opcao != 0:
        print("\n=== MENU GRAFO CIDADE ===")
        print("1 - Imprimir Grafo")
        print("2 - Desenhar Grafo e gerar PNG")
        print("3 - Listar Nós")
        print("4 - Listar Arestas")
        print("5 - Listar Veículos")
        print("0 - Sair")

        try:
            opcao = int(input("Escolha uma opção -> "))
        except ValueError:
            print("⚠️ Opção inválida.")
            continue

        if opcao == 0:
            print("Saindo...")
        elif opcao == 1:
            print(mapa)
            input("Prima Enter para continuar...")
        elif opcao == 2:
            # CORREÇÃO: Chama a função importada
            desenhar_grafo_com_elementos(mapa, veiculos, pedidos)
            input("Prima Enter para continuar...")
        elif opcao == 3:
            print("Nós do grafo:")
            for n in mapa.nos:
                print(" -", n)
            input("Prima Enter para continuar...")
        elif opcao == 4:
            print("Arestas do grafo:")
            for origem, vizinhos in mapa.adj.items():
                for destino, peso in vizinhos.items():
                    print(f"{origem.position} -> {destino.position} | {peso}")
            input("Prima Enter para continuar...")
        elif opcao == 5:
            print("Veículos no sistema:")
            if not veiculos:
                print(" - (Nenhum veículo carregado)")
            else:
                for v in veiculos:
                    # Usa o __repr__ da classe Veiculo
                    print(f" - {v}")
            input("Prima Enter para continuar...")
        else:
            print("⚠️ Opção não reconhecida.")


if __name__ == "__main__":
    main()
