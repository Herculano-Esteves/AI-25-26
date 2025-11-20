import tkinter as tk
from tkinter import ttk
from models.vehicle import Motor
from Simulation.simulator import Simulator
from Simulation.request_simulation import PlanningConfig

import os
import time
from PIL import Image, ImageTk


class MapApplication:
    # GUI constants
    TICK_RATE_MS = 50

    # Navigation constants
    ZOOM_IN_FACTOR = 1.2  # Zoom-in
    ZOOM_OUT_FACTOR = 1 / 1.2  # Zoom-out
    PADDING_RESET = 40  # Extra pixels on reset

    ZOOM_THRESHOLD_TRAFFIC = 10000.0

    # Visual constants
    BG_COLOR = "#2c2c2c"
    EDGE_COLOR = "#4a4a4a"
    NODE_COLOR = "lightblue"
    REQUEST_ACCEPTED_COLOR = "yellow"
    REQUEST_DESTINATION_COLOR = "magenta"
    DEBUG_TEXT_COLOR = "yellow"

    # Drawing constants
    SPRITE_SIZE_PX = 18
    REQUEST_FONT = ("Arial", 20)

    KM_PER_DEGREE_LAT = 130

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota - Painel de Controlo")
        self.root.geometry("1600x1000")

        self.sprite_cache = {}
        try:
            self._load_sprites()
        except Exception as e:
            print(f"Erro fatal ao carregar imagens: {e}")
            print("Verifique se a pasta 'images' existe e contém todos os PNGs necessários.")
            root.destroy()
            return

        self.simulator = Simulator()
        self.simulation_running = False

        # FPS Tracking
        self.last_frame_time = time.time()
        self.fps_avg = 0.0

        # Speed Control Variable
        self.speed_var = tk.DoubleVar(value=1.0)

        # Camera variables
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 20.0  # Pixels per world unit

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_offset_x = 0
        self._drag_start_offset_y = 0

        self._drag_last_x = 0
        self._drag_last_y = 0

        self._create_interface()
        self._setup_bindings()
        self.reset_view()

    def _create_interface(self):
        # TOP CONTROL BAR
        control_frame = ttk.LabelFrame(self.root, text="Controlos de Simulação")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        # Buttons Left
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, padx=10, pady=5)

        # BOTÃO
        self.btn_generate_map = ttk.Button(
            btn_frame, text="Reiniciar Simulação", command=self.setup_new_map
        )
        self.btn_generate_map.pack(side=tk.LEFT, padx=2)

        self.btn_reset_view = ttk.Button(btn_frame, text="Resetar View", command=self.reset_view)
        self.btn_reset_view.pack(side=tk.LEFT, padx=2)

        self.btn_start_sim = ttk.Button(btn_frame, text="▶ Iniciar", command=self.start_simulation)
        self.btn_start_sim.pack(side=tk.LEFT, padx=2)

        self.btn_stop_sim = ttk.Button(
            btn_frame,
            text="⏹ Parar",
            command=self.stop_simulation,
            state=tk.DISABLED,
        )
        self.btn_stop_sim.pack(side=tk.LEFT, padx=2)

        # INFO PANEL (RIGHT SIDE)
        info_panel = ttk.Frame(control_frame)
        info_panel.pack(side=tk.RIGHT, padx=15, pady=2)

        # Date (Small, Top)
        self.date_label = ttk.Label(
            info_panel, text="Ano 0 - Dia 0", font=("Arial", 9), foreground="#666666"
        )
        self.date_label.pack(side=tk.TOP, anchor="e")

        # Time (Big, Middle)
        self.time_label = ttk.Label(
            info_panel, text="08:00", font=("Arial", 22, "bold"), foreground="#000000"
        )
        self.time_label.pack(side=tk.TOP, anchor="e")

        # Weather (Medium, Bottom)
        self.weather_label = ttk.Label(
            info_panel, text="--", font=("Arial", 11)
        )
        self.weather_label.pack(side=tk.TOP, anchor="e")

        # FPS Label (Left of the clock)
        self.fps_label = ttk.Label(control_frame, text="FPS: 0", font=("Consolas", 9))
        self.fps_label.pack(side=tk.RIGHT, padx=20)

        # MAIN SPLIT VIEW
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Map Area
        map_frame = ttk.Frame(self.main_paned_window)
        map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.main_paned_window.add(map_frame, weight=4)

        # Tkinter Map "Canvas"
        self.canvas = tk.Canvas(map_frame, bg=self.BG_COLOR, cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Stats/Config Panel
        self._create_right_panel()
        self.main_paned_window.add(self.stats_frame, weight=1)

    def _create_right_panel(self):
        self.stats_frame = ttk.Frame(self.main_paned_window, width=450)
        self.stats_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook
        self.notebook = ttk.Notebook(self.stats_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        # Vehicles Tab
        self._create_vehicle_tab()

        # Requests Tab
        self._create_request_tab()

        # Metrics Tab
        self._create_metrics_tab()

        # Configuration Tab
        self._create_config_tab()

    def _create_vehicle_tab(self):
        vehicle_tab = ttk.Frame(self.notebook)
        self.notebook.add(vehicle_tab, text="Frota")

        cols = (
            "id",
            "status",
            "autonomy",
            "request",
            "motor",
            "capacidade",
            "co2",
            "station_time",
            "ocup_atual",
            "ocup_media",
            "avarias",
        )
        self.vehicle_tree = ttk.Treeview(vehicle_tab, columns=cols, show="headings")

        # Headers
        headers = {
            "id": ("ID", 35),
            "status": ("Estado", 85),
            "autonomy": ("Bat.", 50),
            "request": ("Req.", 35),
            "motor": ("Tipo", 50),
            "capacidade": ("Pax", 30),
            "co2": ("CO2(kg)", 50),
            "station_time": ("T.Abast", 50),
            "ocup_atual": ("Ocup.Atual", 60),
            "ocup_media": ("Ocup.Média", 60),
            "avarias": ("⚠", 25),
        }
        for col, (text, width) in headers.items():
            self.vehicle_tree.heading(col, text=text)
            self.vehicle_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(vehicle_tab, orient=tk.VERTICAL, command=self.vehicle_tree.yview)
        self.vehicle_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vehicle_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_request_tab(self):
        request_tab = ttk.Frame(self.notebook)
        self.notebook.add(request_tab, text="Pedidos")

        req_cols = ("id", "status", "from", "to", "pax", "pref")
        self.request_tree = ttk.Treeview(request_tab, columns=req_cols, show="headings")

        headers = {
            "id": ("ID", 40),
            "status": ("Estado", 80),
            "from": ("Origem", 70),
            "to": ("Destino", 70),
            "pax": ("Pax", 30),
            "pref": ("Eco", 30),
        }
        for col, (text, width) in headers.items():
            self.request_tree.heading(col, text=text)
            self.request_tree.column(col, width=width)

        req_scrollbar = ttk.Scrollbar(
            request_tab, orient=tk.VERTICAL, command=self.request_tree.yview
        )
        self.request_tree.configure(yscrollcommand=req_scrollbar.set)
        req_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.request_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_metrics_tab(self):
        stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(stats_tab, text="Métricas")

        stats_label_frame = ttk.Frame(stats_tab)
        stats_label_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.stats_labels = {}

        # Create stat rows
        curr_row = 0

        def add_stat_row(key, label_text, init_val, header=False):
            nonlocal curr_row
            if header:
                lbl = ttk.Label(stats_label_frame, text=label_text, font=("Arial", 11, "bold"))
                lbl.grid(
                    row=curr_row,
                    column=0,
                    columnspan=2,
                    sticky=tk.W,
                    pady=(10 if curr_row > 0 else 0, 5),
                )
                self.stats_labels[key] = lbl
            else:
                lbl_t = ttk.Label(stats_label_frame, text=label_text)
                lbl_t.grid(row=curr_row, column=0, sticky=tk.W)
                lbl_v = ttk.Label(stats_label_frame, text=init_val, font=("Arial", 10))
                lbl_v.grid(row=curr_row, column=1, sticky=tk.W, padx=5)
                self.stats_labels[key] = lbl_v
            curr_row += 1

        add_stat_row("h1", "Em Tempo Real (Snapshot)", "", True)
        add_stat_row("step_cost", "Custo Op. Instantâneo:", "€0.00")
        add_stat_row("step_revenue", "Receita Instantânea:", "€0.00")
        add_stat_row("step_pending_req", "Pendentes na Fila:", "0")
        add_stat_row("step_vehicles_busy", "Veículos Ativos:", "0")

        # Financials
        add_stat_row("h2", "Desempenho Financeiro", "", True)
        add_stat_row("total_revenue", "Receita Total:", "€0.00")
        add_stat_row("total_cost", "Custo Op. Total:", "€0.00")
        add_stat_row("total_profit", "Lucro Líquido:", "€0.00")

        # Operations
        add_stat_row("h3", "Eficiência Operacional", "", True)
        add_stat_row("total_requests", "Pedidos (Ok/Fail):", "0 / 0")
        add_stat_row("timeout_cancels", "Cancelados (Timeout):", "0")
        add_stat_row("kms_empty", "Km Vazios (%):", "0%")
        add_stat_row("kms_empty_ev", "Km Vazios EV (%):", "0%")
        add_stat_row("kms_empty_gas", "Km Vazios Gas (%):", "0%")
        add_stat_row("total_co2", "Emissões CO2:", "0.00 kg")
        add_stat_row("loss_time_ev_gas", "Perda Tempo (EV vs Gas):", "0.0m vs 0.0m")

        # Times
        add_stat_row("h4", "Tempo de Serviço (Minutos)", "", True)
        add_stat_row("avg_wait_time", "Espera Média (Recolha):", "0.0 min")
        add_stat_row("range_wait_time", "Espera [Mín - Máx]:", "0.0 - 0.0")
        add_stat_row("avg_trip_time", "Viagem Média (Entrega):", "0.0 min")
        add_stat_row("range_trip_time", "Viagem [Mín - Máx]:", "0.0 - 0.0")

    def _create_config_tab(self):
        """
        Creates controls to change simulation variables dynamically.
        """
        config_tab = ttk.Frame(self.notebook)
        self.notebook.add(config_tab, text="Configurações")

        scroll = ttk.Scrollbar(config_tab)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        canvas = tk.Canvas(config_tab, yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=canvas.yview)

        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def update_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind("<Configure>", update_scroll)

        # Speed control
        ttk.Label(inner_frame, text="Controlo da Simulação", font=("Arial", 12, "bold")).pack(
            pady=(10, 5), anchor=tk.W, padx=5
        )

        speed_frame = ttk.LabelFrame(inner_frame, text="Velocidade do Tempo")
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        self.speed_scale = tk.Scale(
            speed_frame,
            from_=0.1,
            to=10.0,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            resolution=0.1,
            label="Multiplicador (x)",
        )
        self.speed_scale.pack(fill=tk.X, padx=5, pady=5)

        # Tuning section
        ttk.Label(
            inner_frame, text="Pesos do Planeamento (Ao Vivo)", font=("Arial", 12, "bold")
        ).pack(pady=(15, 5), anchor=tk.W, padx=5)

        def create_config_slider(label_text, config_attr, min_val, max_val, resolution=1.0):
            frame = ttk.Frame(inner_frame)
            frame.pack(fill=tk.X, padx=10, pady=2)

            current_val = getattr(PlanningConfig, config_attr)

            lbl = ttk.Label(frame, text=f"{label_text}: {current_val}")
            lbl.pack(anchor=tk.W)

            def on_change(val):
                new_val = float(val)
                setattr(PlanningConfig, config_attr, new_val)
                lbl.config(text=f"{label_text}: {new_val:.1f}")

            scale = tk.Scale(
                frame,
                from_=min_val,
                to=max_val,
                orient=tk.HORIZONTAL,
                resolution=resolution,
                command=on_change,
            )
            scale.set(current_val)
            scale.pack(fill=tk.X)

        # Sliders
        create_config_slider("Peso: Tempo Viagem", "WEIGHT_TIME", 0.1, 10.0, 0.1)
        create_config_slider("Peso: Prioridade", "WEIGHT_PRIORITY", 0, 100, 1)
        create_config_slider("Peso: Tempo Espera (Age)", "WEIGHT_AGE", 0.1, 20.0, 0.1)

        ttk.Separator(inner_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        create_config_slider(
            "Penalidade: Eco Mismatch (/km)", "PENALTY_ENV_MISMATCH_PER_KM", 0, 100, 1
        )
        create_config_slider("Penalidade: Lugar Vazio", "PENALTY_UNUSED_SEAT", 0, 20, 1)
        create_config_slider("Penalidade: Risco Bateria", "WEIGHT_BATTERY_RISK", 0, 100, 1)

        ttk.Separator(inner_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        create_config_slider("Peso: Custo Oportunidade (EV)", "WEIGHT_LOST_OPPORTUNITY", 0, 200, 5)

    def _setup_bindings(self):
        # Linux only
        self.canvas.bind("<Button-4>", self._on_zoom)
        self.canvas.bind("<Button-5>", self._on_zoom)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Configure>", self._on_resize)

    def _load_sprites(self):
        print("A carregar sprites...")
        base_path = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_path, "images")

        sprite_files = {
            "gas": "gas.png",
            "ev": "ev.png",
            "carro_gas": "carro_gas.png",
            "carro_ev": "carro_ev.png",
            "request_wait": "person_blue.png",
            "request_accepted": "person_green.png",
        }

        new_size = (self.SPRITE_SIZE_PX, self.SPRITE_SIZE_PX)

        for name, filename in sprite_files.items():
            try:
                img_path = os.path.join(image_path, filename)
                img = Image.open(img_path)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                self.sprite_cache[name] = ImageTk.PhotoImage(img)

            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Não foi possível encontrar a imagem: {filename} em {image_path}"
                )
            except Exception as e:
                raise IOError(f"Erro ao processar a imagem {filename}: {e}")

        print(f"Sprites carregados com sucesso: {list(self.sprite_cache.keys())}")

    def setup_new_map(self):
        print("A gerar novo map...")
        self.simulator.setup_new_map()
        self._update_clock()
        self.reset_view()

    def reset_view(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            # Canvas not yet ready; try again shortly
            self.root.after(100, self.reset_view)
            return

        city_map = getattr(self.simulator, "map", None)
        if city_map and getattr(city_map, "nos", None):
            nodes = list(city_map.nos)
            if nodes:
                lons = [p.position[0] for p in nodes]
                lats = [p.position[1] for p in nodes]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)

                # world extents
                world_w = max_lon - min_lon if max_lon > min_lon else 1.0
                world_h = max_lat - min_lat if max_lat > min_lat else 1.0

                usable_w = canvas_w - (2 * self.PADDING_RESET)
                usable_h = canvas_h - (2 * self.PADDING_RESET)

                # determine zoom (pixels per degree)
                scale_x = usable_w / world_w
                scale_y = usable_h / world_h
                self.zoom = min(scale_x, scale_y)

                # center on box
                center_lon = (min_lon + max_lon) / 2.0
                center_lat = (min_lat + max_lat) / 2.0

                self.offset_x = (canvas_w / 2.0) - (center_lon * self.zoom)
                self.offset_y = (canvas_h / 2.0) - (-center_lat * self.zoom)

                self.redraw_full_canvas()
                return

        usable_w = canvas_w - (2 * self.PADDING_RESET)
        usable_h = canvas_h - (2 * self.PADDING_RESET)

        map_world_w = self.simulator.MAP_WIDTH - 1 if self.simulator.MAP_WIDTH > 1 else 1
        map_world_h = self.simulator.MAP_HEIGHT - 1 if self.simulator.MAP_HEIGHT > 1 else 1

        scale_x = usable_w / map_world_w
        scale_y = usable_h / map_world_h
        self.zoom = min(scale_x, scale_y)

        map_pixel_w = map_world_w * self.zoom
        map_pixel_h = map_world_h * self.zoom
        self.offset_x = (canvas_w - map_pixel_w) / 2
        self.offset_y = (canvas_h - map_pixel_h) / 2

        self.redraw_full_canvas()

    def start_simulation(self):
        if self.simulation_running:
            return
        print("A iniciar simulação...")
        self.simulation_running = True
        self.last_frame_time = time.time()

        self.btn_start_sim.config(state=tk.DISABLED)
        self.btn_stop_sim.config(state=tk.NORMAL)
        self.btn_generate_map.config(state=tk.DISABLED)
        self.btn_reset_view.config(state=tk.DISABLED)

        self._simulation_gui_loop()

    def stop_simulation(self):
        print("A parar simulação...")
        self.simulation_running = False

        self.btn_start_sim.config(state=tk.NORMAL)
        self.btn_stop_sim.config(state=tk.DISABLED)
        self.btn_generate_map.config(state=tk.NORMAL)
        self.btn_reset_view.config(state=tk.NORMAL)

    def _simulation_gui_loop(self):
        if not self.simulation_running:
            return

        # FPS
        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        if delta_time > 0:
            instant_fps = 1.0 / delta_time
            self.fps_avg = 0.9 * self.fps_avg + 0.1 * instant_fps
            if int(current_time * 10) % 5 == 0:
                self.fps_label.config(text=f"FPS: {self.fps_avg:.1f}")

        # Speed Multiplier from Slider
        speed_mult = self.speed_var.get()

        # Step Simulation
        self.simulator.simulation_step(time_multiplier=speed_mult)

        # Update Visuals
        self.update_dynamic_visuals()
        self._update_stats_panel()
        self._update_clock()

        self.root.after(self.TICK_RATE_MS, self._simulation_gui_loop)

    def _update_stats_panel(self):
        if not self.simulator:
            return

        # Update Vehicle Tab
        self.vehicle_tree.delete(*self.vehicle_tree.get_children())
        for v in self.simulator.vehicles:
            autonomy_str = f"{v.remaining_km:.0f}/{v.max_km:.0f}"
            request_id = v.request.id if v.request else "---"
            status_str = v.condition.name.replace("_", " ").title()
            if status_str == "Unavailable":
                status_str = "Quebrado"

            values = (
                v.id,
                status_str,
                autonomy_str,
                request_id,
                v.motor.name[0:4],  # ELEC/COMB
                v.passenger_capacity,
                f"{v.co2_emitted:.2f}",
                f"{v.total_station_time:.1f}",
                f"{(v.request.passenger_capacity / v.passenger_capacity * 100):.0f}%" if v.request else "0%",
                f"{(v.sum_occupancy / v.total_trips * 100):.0f}%" if v.total_trips > 0 else "0%",
                v.times_borken,
            )
            self.vehicle_tree.insert("", tk.END, values=values)

        # Update Request Tab
        self.request_tree.delete(*self.request_tree.get_children())

        req_list = []

        def add_reqs(source_list, status_code):
            for r in source_list:
                pref_str = "Sim" if r.environmental_preference else "-"
                req_list.append(
                    (
                        r.id,
                        status_code,
                        f"{r.start_node.position}",
                        f"{r.end_node.position}",
                        r.passenger_capacity,
                        pref_str,
                    )
                )

        add_reqs(self.simulator.requests, "Pendente")
        add_reqs(self.simulator.requests_to_pickup, "Apanhar")
        add_reqs(self.simulator.requests_to_dropoff, "Viagem")

        # Sort by ID
        req_list.sort(key=lambda x: x[0])
        for r in req_list:
            self.request_tree.insert("", tk.END, values=r)

        self._update_metrics_values()

    def _update_metrics_values(self):
        stats = self.simulator.stats
        labels = self.stats_labels

        # Snapshot
        labels["step_cost"].config(text=f"€{stats.step_operational_cost:,.2f}")
        labels["step_revenue"].config(text=f"€{stats.step_revenue_generated:,.2f}")
        labels["step_pending_req"].config(text=f"{stats.step_pending_requests}")

        busy_vs = (
            stats.step_vehicles_on_trip
            + stats.step_vehicles_charging
            + stats.step_vehicles_unavailable
        )
        labels["step_vehicles_busy"].config(text=f"{busy_vs}")

        # Financials
        labels["total_revenue"].config(text=f"€{stats.total_revenue_generated:,.2f}")
        labels["total_cost"].config(text=f"€{stats.total_operational_cost:,.2f}")
        profit = stats.total_revenue_generated - stats.total_operational_cost
        labels["total_profit"].config(text=f"€{profit:,.2f}")

        # Operations
        labels["total_requests"].config(
            text=f"{stats.total_requests_completed} / {stats.total_requests_failed}"
        )

        # Cancelled
        labels["timeout_cancels"].config(text=f"{stats.total_requests_cancelled_timeout}")

        empty_ratio = 0.0
        if stats.total_kms_driven > 0:
            empty_ratio = (stats.total_kms_driven_empty / stats.total_kms_driven) * 100
        labels["kms_empty"].config(text=f"{empty_ratio:.1f}%")

        ev_empty_ratio = 0.0
        if stats.total_kms_driven_ev > 0:
            ev_empty_ratio = (stats.total_kms_driven_empty_ev / stats.total_kms_driven_ev) * 100
        labels["kms_empty_ev"].config(text=f"{ev_empty_ratio:.1f}%")

        gas_empty_ratio = 0.0
        if stats.total_kms_driven_gas > 0:
            gas_empty_ratio = (stats.total_kms_driven_empty_gas / stats.total_kms_driven_gas) * 100
        labels["kms_empty_gas"].config(text=f"{gas_empty_ratio:.1f}%")

        # CO2
        labels["total_co2"].config(text=f"{stats.total_co2_emitted:.2f} kg")

        # Lost Time
        labels["loss_time_ev_gas"].config(
            text=f"{stats.total_station_time_ev:.1f}m vs {stats.total_station_time_gas:.1f}m"
        )

        # Times
        # Wait time (Creation -> Pickup)
        avg_wait = 0.0
        if stats.total_requests_picked_up > 0:
            avg_wait = stats.total_wait_time_for_pickup / stats.total_requests_picked_up
        labels["avg_wait_time"].config(text=f"{avg_wait:.1f} min")

        min_wait = 0.0 if stats.min_wait_time == float("inf") else stats.min_wait_time
        labels["range_wait_time"].config(text=f"{min_wait:.1f} - {stats.max_wait_time:.1f}")

        # Trip time (Creation -> Dropoff)
        avg_trip = 0.0
        if stats.total_requests_completed > 0:
            avg_trip = stats.total_time_for_completed_requests / stats.total_requests_completed
        labels["avg_trip_time"].config(text=f"{avg_trip:.1f} min")

        min_trip = 0.0 if stats.min_total_trip_time == float("inf") else stats.min_total_trip_time
        labels["range_trip_time"].config(text=f"{min_trip:.1f} - {stats.max_total_trip_time:.1f}")

    def _update_clock(self):
        current_day, current_hour, current_minute, current_year = (
            self.simulator.get_current_time_of_day()
        )

        self.date_label.config(text=f"Ano {current_year} - Dia {current_day}")
        self.time_label.config(text=f"{current_hour:02d}:{current_minute:02d}")

        # METEOROLOGIA
        if hasattr(self.simulator, "traffic_manager"):
            cond = self.simulator.traffic_manager.current_weather_condition
            
            color = "#000000"
            icon = "☀"
            if cond == "Nublado": 
                icon = "☁"
                color = "#555555"
            elif cond == "Chuva": 
                icon = "🌧"
                color = "#0066cc"
            elif cond == "Tempestade": 
                icon = "⛈"
                color = "#cc0000"
                
            self.weather_label.config(text=f"{icon} {cond}", foreground=color)

    def update_dynamic_visuals(self):
        for v in self.simulator.vehicles:
            vehicle_tag = f"vehicle_{v.id}"
            new_x, new_y = self._world_to_canvas(*v.map_coordinates)
            self.canvas.coords(vehicle_tag, new_x, new_y)

        self._draw_requests()
        self._draw_vehicles()

        self._draw_hotspots()
        self._draw_station_overlays()

        # Redesenhar arestas com trânsito se o zoom for suficiente
        if self.zoom > self.ZOOM_THRESHOLD_TRAFFIC:
            self.canvas.delete("aresta")

            c_width = self.canvas.winfo_width()
            c_height = self.canvas.winfo_height()
            margin = 100

            self._draw_edges(c_width, c_height, margin)

            self.canvas.tag_lower("aresta")
            self.canvas.tag_lower("aresta")

    def _on_resize(self, event):
        self.redraw_full_canvas()

    def _on_zoom(self, event):
        # Linux only
        zoom_factor = 1.0
        if event.num == 4:  # Scroll Up (Zoom In)
            zoom_factor = self.ZOOM_IN_FACTOR
        elif event.num == 5:  # Scroll Down (Zoom Out)
            zoom_factor = self.ZOOM_OUT_FACTOR
        else:
            return
        world_x_before, world_y_before = self._canvas_to_world(event.x, event.y)
        self.zoom *= zoom_factor
        canvas_x_after, canvas_y_after = self._world_to_canvas(world_x_before, world_y_before)
        self.offset_x += event.x - canvas_x_after
        self.offset_y += event.y - canvas_y_after
        self.redraw_full_canvas()

    def _on_drag_start(self, event):
        self.canvas.config(cursor="fleur")
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_start_offset_x = self.offset_x
        self._drag_start_offset_y = self.offset_y

        self._drag_last_x = event.x
        self._drag_last_y = event.y

    def _on_drag_motion(self, event):
        delta_x = event.x - self._drag_last_x
        delta_y = event.y - self._drag_last_y

        # Move
        self.canvas.move("all", delta_x, delta_y)

        # Update offset
        total_delta_x = event.x - self._drag_start_x
        total_delta_y = event.y - self._drag_start_y
        self.offset_x = self._drag_start_offset_x + total_delta_x
        self.offset_y = self._drag_start_offset_y + total_delta_y

        self._drag_last_x = event.x
        self._drag_last_y = event.y

    def _on_drag_end(self, event):
        self.canvas.config(cursor="crosshair")  # Restore cursor
        self.redraw_full_canvas()

    def _world_to_canvas(self, world_x, world_y):
        canvas_x = (world_x * self.zoom) + self.offset_x
        canvas_y = (-world_y * self.zoom) + self.offset_y
        return canvas_x, canvas_y

    def _canvas_to_world(self, canvas_x, canvas_y):
        world_x = (canvas_x - self.offset_x) / self.zoom
        world_y = -(canvas_y - self.offset_y) / self.zoom
        return world_x, world_y

    def redraw_full_canvas(self):
        if not self.simulator.map:
            return

        self.canvas.delete("all")

        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        # Static / Background
        self._draw_edges(c_width, c_height, margin)  # Arestas
        self._draw_nodes(c_width, c_height, margin)  # Estações

        self._draw_hotspots()  # Hotspots
        self._draw_station_overlays()  # Overlays das Estações

        # Dinamic / Foreground
        self._draw_requests()  # Pedidos
        self._draw_vehicles()  # Veículos

        # Debug
        self.canvas.create_text(
            10,
            10,
            anchor=tk.NW,
            fill=self.DEBUG_TEXT_COLOR,
            text=f"Zoom: {self.zoom:.2f} | Offset: ({self.offset_x:.0f}, {self.offset_y:.0f})",
        )

    def _draw_edges(self, c_width, c_height, margin):

        # Flags
        show_traffic = (self.zoom > self.ZOOM_THRESHOLD_TRAFFIC) and (
            hasattr(self.simulator, "traffic_manager")
        )

        for start_node, vizinhos in self.simulator.map.adj.items():
            x1, y1 = self._world_to_canvas(*start_node.position)

            for end_node in vizinhos:
                if id(start_node) < id(end_node):
                    x2, y2 = self._world_to_canvas(*end_node.position)

                    if (
                        max(x1, x2) < -margin
                        or min(x1, x2) > c_width + margin
                        or max(y1, y2) < -margin
                        or min(y1, y2) > c_height + margin
                    ):
                        continue

                    color = self.EDGE_COLOR
                    width = 1

                    if show_traffic and self.simulator.traffic_manager:
                        mid_lon = (start_node.position[0] + end_node.position[0]) / 2
                        mid_lat = (start_node.position[1] + end_node.position[1]) / 2

                        factor = self.simulator.traffic_manager.get_traffic_factor(
                            (mid_lon, mid_lat), self.simulator.current_time
                        )

                        if factor > 1.5:
                            color = "#ff4444"
                            width = 2
                        elif factor > 1.1:
                            color = "#ffbb33"
                            width = 2

                    self.canvas.create_line(
                        x1, y1, x2, y2, fill=color, width=width, tags=("aresta",)
                    )

    def _draw_nodes(self, c_width, c_height, margin):
        sprite_gas = self.sprite_cache["gas"]
        sprite_ev = self.sprite_cache["ev"]
        if hasattr(self.simulator.map, "gas_stations"):
            for node in self.simulator.map.gas_stations:
                x, y = self._world_to_canvas(*node.position)

                # Culling
                if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                    continue

                self.canvas.create_image(x, y, image=sprite_gas, tags=("no", "posto_gas"))

        if hasattr(self.simulator.map, "ev_stations"):
            for node in self.simulator.map.ev_stations:
                x, y = self._world_to_canvas(*node.position)

                if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                    continue

                self.canvas.create_image(x, y, image=sprite_ev, tags=("no", "posto_ev"))

    def _draw_station_overlays(self):
        # Delete old crosses
        self.canvas.delete("falha_overlay")

        overlay_radius = self.SPRITE_SIZE_PX / 2.5

        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        stations_to_check = []
        if hasattr(self.simulator.map, "gas_stations"):
            stations_to_check.extend(self.simulator.map.gas_stations)
        if hasattr(self.simulator.map, "ev_stations"):
            stations_to_check.extend(self.simulator.map.ev_stations)

        for node in stations_to_check:
            if not node.is_available:
                x, y = self._world_to_canvas(*node.position)

                if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                    continue

                # Draw the cross
                self.canvas.create_line(
                    x - overlay_radius,
                    y - overlay_radius,
                    x + overlay_radius,
                    y + overlay_radius,
                    fill="red",
                    width=4,
                    tags=("no", "falha_overlay"),
                )
                self.canvas.create_line(
                    x - overlay_radius,
                    y + overlay_radius,
                    x + overlay_radius,
                    y - overlay_radius,
                    fill="red",
                    width=4,
                    tags=("no", "falha_overlay"),
                )

    def _draw_requests(self):
        self.canvas.delete("request")
        sprite_request_wait = self.sprite_cache["request_wait"]
        sprite_request_accepted = self.sprite_cache["request_accepted"]

        for p in self.simulator.requests:
            x, y = self._world_to_canvas(*p.start_node.position)
            self.canvas.create_image(
                x,
                y - 10,
                image=sprite_request_wait,
                tags=("request", f"request_{p.id}"),
            )

        for p in self.simulator.requests_to_pickup:
            x, y = self._world_to_canvas(*p.start_node.position)
            self.canvas.create_image(
                x,
                y - 10,
                image=sprite_request_accepted,
                tags=("request", f"request_{p.id}"),
            )

        for p in self.simulator.requests_to_dropoff:
            x, y = self._world_to_canvas(*p.end_node.position)
            self.canvas.create_text(
                x,
                y,
                text="⚑",
                fill=self.REQUEST_DESTINATION_COLOR,
                font=self.REQUEST_FONT,
                tags=("request", f"request_{p.id}"),
            )

    def _draw_vehicles(self):
        self.canvas.delete("vehicle")

        sprite_ev = self.sprite_cache["carro_ev"]
        sprite_gas = self.sprite_cache["carro_gas"]

        for v in self.simulator.vehicles:
            x, y = self._world_to_canvas(*v.map_coordinates)

            sprite_to_use = sprite_ev if v.motor == Motor.ELECTRIC else sprite_gas

            self.canvas.create_image(
                x,
                y,
                image=sprite_to_use,
                tags=("vehicle", f"vehicle_{v.id}"),
            )

    def _draw_hotspots(self):
        if not self.simulator.hotspot_manager:
            return

        self.canvas.delete("hotspot")
        hotspots = self.simulator.hotspot_manager.hotspots

        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        KM_PER_DEGREE = self.KM_PER_DEGREE_LAT

        for h in hotspots:
            x, y = self._world_to_canvas(*h.coordinates)

            # Radius in pixels
            # (Raio em KM / Constante de conversão) * Zoom
            radius_pixels = (h.radius_km / KM_PER_DEGREE) * self.zoom

            # Culling
            if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                continue

            if h.is_active:
                outline_color = "green"
            else:
                outline_color = "red"

            self.canvas.create_oval(
                x - radius_pixels,
                y - radius_pixels,
                x + radius_pixels,
                y + radius_pixels,
                outline=outline_color,
                width=2,
                tags="hotspot",
            )

            # Draw text
            if self.zoom > 10000:
                font_size = min(int(self.zoom / 10000 * 5), 15)

                if font_size > 0:
                    self.canvas.create_text(
                        x,
                        y,
                        text=h.name,
                        fill="white",
                        font=("Arial", font_size, "bold"),
                        tags="hotspot",
                    )


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApplication(root)
    root.mainloop()
