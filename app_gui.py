import tkinter as tk
from tkinter import ttk
import random

from main import criar_mapa_gerado
from models import Motorizacao


class MapApplication:
    # Constantes de Configuração
    LARGURA_MAPA = 20
    ALTURA_MAPA = 20

    TICK_RATE_MS = 40  # 25 FPS
    SIM_TEMPO_POR_TICK = 0.1  # Tempo em minutos por tick 2.5 minutos / segundo

    # Constantes de Navegação
    ZOOM_IN_FACTOR = 1.2  # Fator de zoom-in
    ZOOM_OUT_FACTOR = 1 / 1.2  # Fator de zoom-out
    PADDING_RESET = 40  # Pixels de margem ao resetar a view

    # Constantes Visuais
    COR_FUNDO = "#2c2c2c"
    COR_ARESTA = "#4a4a4a"
    COR_NO = "lightblue"
    COR_GAS = "orange"
    COR_EV = "limegreen"
    COR_PEDIDO = "deep sky blue"
    COR_VEICULO_EV = "green"
    COR_VEICULO_GAS = "red"
    COR_DEBUG_TEXT = "yellow"

    # Constantes Visuais (Tamanhos/Formas)
    # (Tamanhos em pixels, não escalam com o zoom)
    NO_RAIO = 4
    POSTO_LADO = 6
    EV_RAIO = 7
    VEICULO_SHAPE = [0, -8, -6, 5, 6, 5]  # Pontos (x,y) relativos ao centro
    PEDIDO_FONTE = ("Arial", 20)

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota")
        self.root.geometry("1000x1000")

        # Variáveis de Estado da Simulação
        self.mapa = None
        self.veiculos = []
        self.pedidos = []
        self.simulacao_a_correr = False

        # Variáveis de Controlo da "Câmara" (View)
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 20.0  # Pixels por unidade do mapa

        # Variáveis de Controlo de Arrastar (Drag)
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_offset_x = 0
        self._drag_start_offset_y = 0

        # Configuração da Interface
        self._criar_interface()
        self._configurar_bindings()

        # Desenho Inicial
        print("A gerar mapa inicial...")
        self.configurar_novo_mapa()

    def _criar_interface(self):
        # Frame de Controlo (para botões)
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        self.btn_gerar_mapa = ttk.Button(
            control_frame, text="Gerar Novo Mapa", command=self.configurar_novo_mapa
        )
        self.btn_gerar_mapa.pack(side=tk.LEFT, padx=5)

        self.btn_reset_view = ttk.Button(
            control_frame, text="Resetar View", command=self.resetar_view
        )
        self.btn_reset_view.pack(side=tk.LEFT, padx=5)

        self.btn_iniciar_sim = ttk.Button(
            control_frame, text="Iniciar Simulação", command=self.iniciar_simulacao
        )
        self.btn_iniciar_sim.pack(side=tk.LEFT, padx=5)

        self.btn_parar_sim = ttk.Button(
            control_frame,
            text="Parar Simulação",
            command=self.parar_simulacao,
            state=tk.DISABLED,
        )
        self.btn_parar_sim.pack(side=tk.LEFT, padx=5)

        # Frame do Canvas
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Configuração do Canvas Tkinter
        self.canvas = tk.Canvas(canvas_frame, bg=self.COR_FUNDO, cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _configurar_bindings(self):
        # APENAS LINUX

        self.canvas.bind("<Button-4>", self._ao_dar_zoom)
        self.canvas.bind("<Button-5>", self._ao_dar_zoom)

        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)

        self.canvas.bind("<Configure>", self._ao_redimensionar)

    # 1. Métodos de Controlo Público

    def configurar_novo_mapa(self):
        print("A gerar novo mapa...")
        self.mapa, self.veiculos, self.pedidos = criar_mapa_gerado(
            self.LARGURA_MAPA, self.ALTURA_MAPA, 0.03, 0.01
        )
        self.resetar_view()

    def resetar_view(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            # Se o canvas ainda não foi desenhado, tenta de novo
            self.root.after(100, self.resetar_view)
            return

        # 1. Calcular o zoom ideal (para caber tudo com padding)
        util_w = canvas_w - (2 * self.PADDING_RESET)
        util_h = canvas_h - (2 * self.PADDING_RESET)

        map_w_mundo = self.LARGURA_MAPA - 1 if self.LARGURA_MAPA > 1 else 1
        map_h_mundo = self.ALTURA_MAPA - 1 if self.ALTURA_MAPA > 1 else 1

        escala_x = util_w / map_w_mundo
        escala_y = util_h / map_h_mundo
        self.zoom = min(escala_x, escala_y)

        # 2. Calcular o offset ideal (para centrar)
        mapa_pixel_w = map_w_mundo * self.zoom
        mapa_pixel_h = map_h_mundo * self.zoom
        self.offset_x = (canvas_w - mapa_pixel_w) / 2
        self.offset_y = (canvas_h - mapa_pixel_h) / 2

        # 3. Redesenhar tudo
        self.redesenhar_canvas_completo()

    def iniciar_simulacao(self):
        """Inicia o loop da simulação."""
        if self.simulacao_a_correr:
            return
        print("Iniciando simulação...")
        self.simulacao_a_correr = True

        # Atualiza estado dos botões
        self.btn_iniciar_sim.config(state=tk.DISABLED)
        self.btn_parar_sim.config(state=tk.NORMAL)
        self.btn_gerar_mapa.config(state=tk.DISABLED)
        self.btn_reset_view.config(state=tk.DISABLED)

        self.passo_simulacao()

    def parar_simulacao(self):
        """Para o loop da simulação."""
        print("Parando simulação...")
        self.simulacao_a_correr = False

        # Atualiza estado dos botões
        self.btn_iniciar_sim.config(state=tk.NORMAL)
        self.btn_parar_sim.config(state=tk.DISABLED)
        self.btn_gerar_mapa.config(state=tk.NORMAL)
        self.btn_reset_view.config(state=tk.NORMAL)

    # 2. Loop da Simulação

    def passo_simulacao(self):
        if not self.simulacao_a_correr:
            return

        tempo_a_avancar = self.SIM_TEMPO_POR_TICK

        for v in self.veiculos:
            # Verifica se o veículo está em movimento
            if v.nodo_destino:
                v.tempo_viagem_passado += tempo_a_avancar

                if v.tempo_viagem_passado >= v.tempo_viagem_total:
                    # Em destino
                    v.nodo_atual = v.nodo_destino
                    v.nodo_origem = None
                    v.nodo_destino = None
                    v.tempo_viagem_passado = 0
                    v.localizacao_atual_coords = v.nodo_atual.position
                else:
                    # Em trânsito
                    # Calcula o progresso (0.0 a 1.0)
                    progresso = v.tempo_viagem_passado / v.tempo_viagem_total

                    # Interpolação Linear (Lerp)
                    x1, y1 = v.nodo_origem.position
                    x2, y2 = v.nodo_destino.position

                    novo_x = x1 + (x2 - x1) * progresso
                    novo_y = y1 + (y2 - y1) * progresso

                    v.localizacao_atual_coords = (novo_x, novo_y)

            else:
                # O VEÍCULO ESTÁ PARADO
                # Encontra um novo destino aleatório

                if not self.mapa or not self.mapa.obter_vizinhos(v.nodo_atual):
                    continue

                vizinhos = self.mapa.obter_vizinhos(v.nodo_atual)
                if vizinhos:
                    novo_destino = random.choice(vizinhos)

                    # (dist, tempo)
                    aresta_info = self.mapa.obter_peso_aresta(
                        v.nodo_atual, novo_destino
                    )

                    # Verifica se a aresta existe
                    if aresta_info:
                        _, tempo_viagem = aresta_info

                        v.nodo_origem = v.nodo_atual
                        v.nodo_destino = novo_destino
                        v.tempo_viagem_total = tempo_viagem
                        v.tempo_viagem_passado = 0.0
                        v.localizacao_atual_coords = v.nodo_origem.position

        self.atualizar_visuais_dinamicos()

        self.root.after(self.TICK_RATE_MS, self.passo_simulacao)

    def atualizar_visuais_dinamicos(self):
        # Somente atualiza objetos dinâmicos
        for v in self.veiculos:
            tag_veiculo = f"veiculo_{v.id_veiculo}"
            novo_x, novo_y = self._transformar_coords(*v.localizacao_atual_coords)
            self.canvas.coords(tag_veiculo, *self._get_pontos_veiculo(novo_x, novo_y))
        # self._desenhar_pedidos()

    # 3. Handlers de Eventos

    def _ao_redimensionar(self, event):
        self.redesenhar_canvas_completo()

    def _ao_dar_zoom(self, event):
        # Apenas Linux

        fator_zoom = 1.0
        if event.num == 4:  # Scroll Up (Zoom In)
            fator_zoom = self.ZOOM_IN_FACTOR
        elif event.num == 5:  # Scroll Down (Zoom Out)
            fator_zoom = self.ZOOM_OUT_FACTOR
        else:
            return

        mundo_x_antes, mundo_y_antes = self._canvas_para_mundo(event.x, event.y)

        self.zoom *= fator_zoom

        canvas_x_depois, canvas_y_depois = self._transformar_coords(
            mundo_x_antes, mundo_y_antes
        )

        self.offset_x += event.x - canvas_x_depois
        self.offset_y += event.y - canvas_y_depois

        self.redesenhar_canvas_completo()

    def _on_drag_start(self, event):
        self.canvas.config(cursor="fleur")  # Mudar para "mover"
        # Guarda a posição inicial do rato e do offset
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_start_offset_x = self.offset_x
        self._drag_start_offset_y = self.offset_y

    def _on_drag_motion(self, event):
        # Calcula o delta do movimento do rato
        delta_x = event.x - self._drag_start_x
        delta_y = event.y - self._drag_start_y

        # Aplica o delta ao offset inicial
        self.offset_x = self._drag_start_offset_x + delta_x
        self.offset_y = self._drag_start_offset_y + delta_y

        # Redesenha o canvas
        self.redesenhar_canvas_completo()

    def _on_drag_end(self, event):
        self.canvas.config(cursor="crosshair")  # Restaura cursor original

    # 4. Lógica de Coordenadas (Privada)

    def _transformar_coords(self, x_mundo, y_mundo):
        canvas_x = (x_mundo * self.zoom) + self.offset_x
        canvas_y = (y_mundo * self.zoom) + self.offset_y
        return canvas_x, canvas_y

    def _canvas_para_mundo(self, canvas_x, canvas_y):
        mundo_x = (canvas_x - self.offset_x) / self.zoom
        mundo_y = (canvas_y - self.offset_y) / self.zoom
        return mundo_x, mundo_y

    def _get_pontos_veiculo(self, x_centro, y_centro):
        pontos = []
        for i in range(0, len(self.VEICULO_SHAPE), 2):
            pontos.append(x_centro + self.VEICULO_SHAPE[i])
            pontos.append(y_centro + self.VEICULO_SHAPE[i + 1])
        return pontos

    # 5. Funções de Desenho (Privadas)

    def redesenhar_canvas_completo(self):
        if not self.mapa:
            return

        self.canvas.delete("all")

        # Desenha por ordem (de baixo para cima)
        self._desenhar_arestas()
        self._desenhar_nos()
        self._desenhar_pedidos()
        self._desenhar_veiculos()

        # Mostra info de debug
        self.canvas.create_text(
            10,
            10,
            anchor=tk.NW,
            fill=self.COR_DEBUG_TEXT,
            text=f"Zoom: {self.zoom:.2f} | Offset: ({self.offset_x:.0f}, {self.offset_y:.0f})",
        )

    def _desenhar_arestas(self):
        for origem, vizinhos in self.mapa.adj.items():
            x1, y1 = self._transformar_coords(*origem.position)
            for destino in vizinhos:
                if origem == destino:
                    continue
                x2, y2 = self._transformar_coords(*destino.position)
                self.canvas.create_line(
                    x1, y1, x2, y2, fill=self.COR_ARESTA, width=1, tags=("aresta",)
                )

    def _desenhar_nos(self):
        r_no = self.NO_RAIO
        r_posto = self.POSTO_LADO
        r_ev = self.EV_RAIO

        for no in self.mapa.nos:
            x, y = self._transformar_coords(*no.position)

            if no.gas_pumps > 0:
                self.canvas.create_rectangle(
                    x - r_posto,
                    y - r_posto,
                    x + r_posto,
                    y + r_posto,
                    fill=self.COR_GAS,
                    outline="white",
                    tags=("no", "posto_gas"),
                )
            elif no.energy_chargers > 0:
                self.canvas.create_polygon(
                    x,
                    y - r_ev,
                    x + r_ev,
                    y,
                    x,
                    y + r_ev,
                    x - r_ev,
                    y,
                    fill=self.COR_EV,
                    outline="white",
                    tags=("no", "posto_ev"),
                )
            else:
                self.canvas.create_oval(
                    x - r_no,
                    y - r_no,
                    x + r_no,
                    y + r_no,
                    fill=self.COR_NO,
                    outline=self.COR_ARESTA,
                    tags=("no", "no_normal"),
                )

    def _desenhar_pedidos(self):
        self.canvas.delete("pedido")
        for p in self.pedidos:
            x, y = self._transformar_coords(*p.origem.position)
            self.canvas.create_text(
                x,
                y,
                text="★",
                fill=self.COR_PEDIDO,
                font=self.PEDIDO_FONTE,
                tags=("pedido", f"pedido_{p.id_pedido}"),
            )

    def _desenhar_veiculos(self):
        self.canvas.delete("veiculo")
        for v in self.veiculos:
            x, y = self._transformar_coords(*v.localizacao_atual_coords)
            cor = (
                self.COR_VEICULO_EV
                if v.motorizacao == Motorizacao.ELETRICO
                else self.COR_VEICULO_GAS
            )

            self.canvas.create_polygon(
                *self._get_pontos_veiculo(x, y),
                fill=cor,
                outline="black",
                width=1,
                tags=("veiculo", f"veiculo_{v.id_veiculo}"),
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApplication(root)
    root.mainloop()
