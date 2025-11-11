import tkinter as tk
from tkinter import ttk
from models.vehicle import Motor
from Simulation.simulator import Simulator

import os
from PIL import Image, ImageTk


class MapApplication:
    # GUI constants
    TICK_RATE_MS = 5

    # Navigation constants
    ZOOM_IN_FACTOR = 1.2  # Zoom-in
    ZOOM_OUT_FACTOR = 1 / 1.2  # Zoom-out
    PADDING_RESET = 40  # Extra pixels on reset

    # Visual constants
    BG_COLOR = "#2c2c2c"
    EDGE_COLOR = "#4a4a4a"
    NODE_COLOR = "lightblue"
    REQUEST_ACCEPTED_COLOR = "yellow"
    REQUEST_DESTINATION_COLOR = "magenta"
    DEBUG_TEXT_COLOR = "yellow"

    # Drawing constants
    SPRITE_SIZE_PX = 24
    REQUEST_FONT = ("Arial", 20)

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota")
        self.root.geometry("1400x1000")

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
        # Buttons frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        self.btn_generate_map = ttk.Button(
            control_frame, text="Gerar Novo Mapa", command=self.setup_new_map
        )
        self.btn_generate_map.pack(side=tk.LEFT, padx=5)

        self.btn_reset_view = ttk.Button(
            control_frame, text="Resetar View", command=self.reset_view
        )
        self.btn_reset_view.pack(side=tk.LEFT, padx=5)

        self.btn_start_sim = ttk.Button(
            control_frame, text="Iniciar Simulação", command=self.start_simulation
        )
        self.btn_start_sim.pack(side=tk.LEFT, padx=5)

        self.btn_stop_sim = ttk.Button(
            control_frame,
            text="Parar Simulação",
            command=self.stop_simulation,
            state=tk.DISABLED,
        )
        self.btn_stop_sim.pack(side=tk.LEFT, padx=5)

        # Style for the clock
        ttk.Style().configure("Clock.TLabel", font=("Arial", 16, "bold"))

        self.clock_label = ttk.Label(
            control_frame, text="Ano 0 - Dia 0 - 00:00", style="Clock.TLabel"
        )
        self.clock_label.pack(side=tk.RIGHT, padx=15)

        # PanedWindow
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Map
        map_frame = ttk.Frame(self.main_paned_window)
        map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.main_paned_window.add(map_frame, weight=3)  # Map gets 3/4 space

        # Tkinter Map "Canvas"
        self.canvas = tk.Canvas(map_frame, bg=self.BG_COLOR, cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Stats Panel
        self._create_stats_panel()
        self.main_paned_window.add(self.stats_frame, weight=1)  # Stats get 1/4 space

    def _create_stats_panel(self):
        self.stats_frame = ttk.Frame(self.main_paned_window, width=400)
        self.stats_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook
        notebook = ttk.Notebook(self.stats_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        # Vehicles
        vehicle_tab = ttk.Frame(notebook)
        notebook.add(vehicle_tab, text="Frota (Veículos)")

        # Treeview for vehicle
        cols = ("id", "status", "autonomy", "request", "motor", "capacidade", "avarias")
        self.vehicle_tree = ttk.Treeview(vehicle_tab, columns=cols, show="headings")

        self.vehicle_tree.heading("id", text="ID")
        self.vehicle_tree.heading("status", text="Estado")
        self.vehicle_tree.heading("autonomy", text="Autonomia")
        self.vehicle_tree.heading("request", text="Pedido")
        self.vehicle_tree.heading("motor", text="Motor")
        self.vehicle_tree.heading("capacidade", text="Cap.")
        self.vehicle_tree.heading("avarias", text="Avaria")

        self.vehicle_tree.column("id", width=40)
        self.vehicle_tree.column("status", width=120)
        self.vehicle_tree.column("autonomy", width=90)
        self.vehicle_tree.column("request", width=60)
        self.vehicle_tree.column("motor", width=65)
        self.vehicle_tree.column("capacidade", width=40)
        self.vehicle_tree.column("avarias", width=40)

        # Sscrollbar
        scrollbar = ttk.Scrollbar(vehicle_tab, orient=tk.VERTICAL, command=self.vehicle_tree.yview)
        self.vehicle_tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vehicle_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Requests
        request_tab = ttk.Frame(notebook)
        notebook.add(request_tab, text="Pedidos")

        # Treeview for request
        req_cols = ("id", "status", "from", "to", "pax", "pref")
        self.request_tree = ttk.Treeview(request_tab, columns=req_cols, show="headings")

        self.request_tree.heading("id", text="ID")
        self.request_tree.heading("status", text="Estado")
        self.request_tree.heading("from", text="Origem")
        self.request_tree.heading("to", text="Destino")
        self.request_tree.heading("pax", text="Cap.")
        self.request_tree.heading("pref", text="Pref.")

        self.request_tree.column("id", width=40)
        self.request_tree.column("status", width=100)
        self.request_tree.column("from", width=80)
        self.request_tree.column("to", width=80)
        self.request_tree.column("pax", width=40)
        self.request_tree.column("pref", width=60)

        # Scrollbar
        req_scrollbar = ttk.Scrollbar(
            request_tab, orient=tk.VERTICAL, command=self.request_tree.yview
        )
        self.request_tree.configure(yscrollcommand=req_scrollbar.set)

        req_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.request_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Statics bar
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Métricas")

        stats_label_frame = ttk.Frame(stats_tab)
        stats_label_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.stats_labels = {}
        row_idx = 0

        # Frame stats
        self.stats_labels["step_header"] = ttk.Label(
            stats_label_frame, text="Snapshot da Iteração", font=("Arial", 12, "bold")
        )
        self.stats_labels["step_header"].grid(
            row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        row_idx += 1

        # Search cost
        self.stats_labels["step_assign_cost_label"] = ttk.Label(
            stats_label_frame, text="Custo Procura (Atrib.):"
        )
        self.stats_labels["step_assign_cost_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_assign_cost"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["step_assign_cost"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Operacional cost
        self.stats_labels["step_cost_label"] = ttk.Label(
            stats_label_frame, text="Custo Op. (Iteração):"
        )
        self.stats_labels["step_cost_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_cost"] = ttk.Label(stats_label_frame, text="€0.00")
        self.stats_labels["step_cost"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Profit
        self.stats_labels["step_revenue_label"] = ttk.Label(
            stats_label_frame, text="Receita (Iteração):"
        )
        self.stats_labels["step_revenue_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_revenue"] = ttk.Label(stats_label_frame, text="€0.00")
        self.stats_labels["step_revenue"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Pending Requests
        self.stats_labels["step_pending_req_label"] = ttk.Label(
            stats_label_frame, text="Pedidos Pendentes:"
        )
        self.stats_labels["step_pending_req_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_pending_req"] = ttk.Label(stats_label_frame, text="0")
        self.stats_labels["step_pending_req"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Avaliable vehicles
        self.stats_labels["step_vehicles_avail_label"] = ttk.Label(
            stats_label_frame, text="Veículos Livres:"
        )
        self.stats_labels["step_vehicles_avail_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_vehicles_avail"] = ttk.Label(stats_label_frame, text="0")
        self.stats_labels["step_vehicles_avail"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Unavailabe Vehicles
        self.stats_labels["step_vehicles_busy_label"] = ttk.Label(
            stats_label_frame, text="Veículos Ocupados:"
        )
        self.stats_labels["step_vehicles_busy_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["step_vehicles_busy"] = ttk.Label(stats_label_frame, text="0")
        self.stats_labels["step_vehicles_busy"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Total stats
        self.stats_labels["total_header"] = ttk.Label(
            stats_label_frame, text="Desempenho Acumulado", font=("Arial", 12, "bold")
        )
        self.stats_labels["total_header"].grid(
            row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(15, 5)
        )
        row_idx += 1

        # Money related
        self.stats_labels["total_revenue_label"] = ttk.Label(
            stats_label_frame, text="Receita Total:"
        )
        self.stats_labels["total_revenue_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["total_revenue"] = ttk.Label(stats_label_frame, text="€0.00")
        self.stats_labels["total_revenue"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["total_cost_label"] = ttk.Label(
            stats_label_frame, text="Custo Op. Total:"
        )
        self.stats_labels["total_cost_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["total_cost"] = ttk.Label(stats_label_frame, text="€0.00")
        self.stats_labels["total_cost"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["total_profit_label"] = ttk.Label(stats_label_frame, text="Lucro Total:")
        self.stats_labels["total_profit_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["total_profit"] = ttk.Label(stats_label_frame, text="€0.00")
        self.stats_labels["total_profit"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Requests
        self.stats_labels["total_requests_label"] = ttk.Label(
            stats_label_frame, text="Pedidos (Comp./Falh.):"
        )
        self.stats_labels["total_requests_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["total_requests"] = ttk.Label(stats_label_frame, text="0 / 0")
        self.stats_labels["total_requests"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Kms
        self.stats_labels["kms_empty_label"] = ttk.Label(stats_label_frame, text="Kms Vazios (%):")
        self.stats_labels["kms_empty_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["kms_empty"] = ttk.Label(stats_label_frame, text="0.0% (0 km)")
        self.stats_labels["kms_empty"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Wait time
        self.stats_labels["wait_time_header"] = ttk.Label(
            stats_label_frame,
            text="Tempo de Espera (Criação -> Recolha)",
            font=("Arial", 10, "bold"),
        )
        self.stats_labels["wait_time_header"].grid(
            row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(10, 0)
        )
        row_idx += 1

        self.stats_labels["avg_wait_time_label"] = ttk.Label(
            stats_label_frame, text="Espera Média:"
        )
        self.stats_labels["avg_wait_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["avg_wait_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["avg_wait_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["min_wait_time_label"] = ttk.Label(stats_label_frame, text="Espera Mín:")
        self.stats_labels["min_wait_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["min_wait_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["min_wait_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["max_wait_time_label"] = ttk.Label(stats_label_frame, text="Espera Máx:")
        self.stats_labels["max_wait_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["max_wait_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["max_wait_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Trip Time
        self.stats_labels["trip_time_header"] = ttk.Label(
            stats_label_frame,
            text="Tempo de Pedido (Criação -> Entrega)",
            font=("Arial", 10, "bold"),
        )
        self.stats_labels["trip_time_header"].grid(
            row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=(10, 0)
        )
        row_idx += 1

        self.stats_labels["avg_time_label"] = ttk.Label(stats_label_frame, text="Pedido Médio:")
        self.stats_labels["avg_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["avg_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["avg_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["min_trip_time_label"] = ttk.Label(stats_label_frame, text="Pedido Mín:")
        self.stats_labels["min_trip_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["min_trip_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["min_trip_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        self.stats_labels["max_trip_time_label"] = ttk.Label(stats_label_frame, text="Pedido Máx:")
        self.stats_labels["max_trip_time_label"].grid(row=row_idx, column=0, sticky=tk.W)
        self.stats_labels["max_trip_time"] = ttk.Label(stats_label_frame, text="0.0 min")
        self.stats_labels["max_trip_time"].grid(row=row_idx, column=1, sticky=tk.W)
        row_idx += 1

        # Style
        ttk.Style().configure("Stats.TLabel", font=("Arial", 12))
        ttk.Style().configure("StatsVal.TLabel", font=("Arial", 12, "bold"))

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
                self.offset_y = (canvas_h / 2.0) - (center_lat * self.zoom)

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

        self.simulator.simulation_step()  # 1 simulation frame
        self.update_dynamic_visuals()  # Visual update
        self._update_stats_panel()  # Update stats panel
        self._update_clock()  # Update clock
        self.root.after(self.TICK_RATE_MS, self._simulation_gui_loop)  # Next frame

    def _update_stats_panel(self):
        if not self.simulator:
            return

        # Update Vehicle Tab
        self.vehicle_tree.delete(*self.vehicle_tree.get_children())  # Clear old data
        for v in self.simulator.vehicles:
            autonomy_str = f"{v.remaining_km:.1f} / {v.max_km:.0f} km"
            request_id = v.request.id if v.request else "---"
            status_str = v.condition.name.replace("_", " ").title()

            values = (
                v.id,
                status_str,
                autonomy_str,
                request_id,
                v.motor.name.title(),
                v.passenger_capacity,
                v.times_borken,
            )
            self.vehicle_tree.insert("", tk.END, values=values)

        # Update Request Tab
        self.request_tree.delete(*self.request_tree.get_children())  # Clear old data

        def format_request_values(req, status):
            pref_str = "EV" if req.environmental_preference else "---"
            return (
                req.id,
                status,
                str(req.start_node.position),
                str(req.end_node.position),
                req.passenger_capacity,
                pref_str,
            )

        # Requests from all three lists
        lista = list()
        for r in self.simulator.requests:
            lista.append(format_request_values(r, "Pendente"))

        for r in self.simulator.requests_to_pickup:
            lista.append(format_request_values(r, "Apanhar"))

        for r in self.simulator.requests_to_dropoff:
            lista.append(format_request_values(r, "Viagem"))

        for r in sorted(lista):
            self.request_tree.insert("", tk.END, values=r)

        self._update_stats_tab()

    def _update_stats_tab(self):
        stats = self.simulator.stats

        # Frame stats
        self.stats_labels["step_assign_cost"].config(text=f"{stats.step_assignment_cost:,.1f} min")
        self.stats_labels["step_cost"].config(text=f"€{stats.step_operational_cost:,.2f}")
        self.stats_labels["step_revenue"].config(text=f"€{stats.step_revenue_generated:,.2f}")
        self.stats_labels["step_pending_req"].config(text=f"{stats.step_pending_requests}")
        self.stats_labels["step_vehicles_avail"].config(text=f"{stats.step_vehicles_available}")

        # Unavailabe Vehicles
        busy_vehicles = (
            stats.step_vehicles_on_trip
            + stats.step_vehicles_charging
            + stats.step_vehicles_unavailable
        )
        self.stats_labels["step_vehicles_busy"].config(text=f"{busy_vehicles}")

        # Total stats

        # Money related
        self.stats_labels["total_revenue"].config(text=f"€{stats.total_revenue_generated:,.2f}")
        self.stats_labels["total_cost"].config(text=f"€{stats.total_operational_cost:,.2f}")
        total_profit = stats.total_revenue_generated - stats.total_operational_cost
        self.stats_labels["total_profit"].config(text=f"€{total_profit:,.2f}")

        # Requests
        req_str = f"{stats.total_requests_completed} / {stats.total_requests_failed}"
        self.stats_labels["total_requests"].config(text=req_str)

        # % km empty
        empty_ratio = 0.0
        if stats.total_kms_driven > 0:
            empty_ratio = (stats.total_kms_driven_empty / stats.total_kms_driven) * 100
        empty_str = f"{empty_ratio:,.1f}% ({stats.total_kms_driven_empty:,.0f} km)"
        self.stats_labels["kms_empty"].config(text=empty_str)

        # Wait time for pick up
        avg_wait_time = 0.0
        if stats.total_requests_picked_up > 0:
            avg_wait_time = stats.total_wait_time_for_pickup / stats.total_requests_picked_up
        self.stats_labels["avg_wait_time"].config(text=f"{avg_wait_time:,.1f} min")

        min_wait = 0.0 if stats.min_wait_time == float("inf") else stats.min_wait_time
        self.stats_labels["min_wait_time"].config(text=f"{min_wait:,.1f} min")
        self.stats_labels["max_wait_time"].config(text=f"{stats.max_wait_time:,.1f} min")

        # Total request time
        avg_time = 0.0
        if stats.total_requests_completed > 0:
            avg_time = stats.total_time_for_completed_requests / stats.total_requests_completed
        self.stats_labels["avg_time"].config(text=f"{avg_time:,.1f} min")

        min_trip = 0.0 if stats.min_total_trip_time == float("inf") else stats.min_total_trip_time
        self.stats_labels["min_trip_time"].config(text=f"{min_trip:,.1f} min")
        self.stats_labels["max_trip_time"].config(text=f"{stats.max_total_trip_time:,.1f} min")

    def _update_clock(self):
        current_day, current_hour, current_minute, current_year = (
            self.simulator.get_current_time_of_day()
        )

        # Format the string (e.g., "Dia 0 - 08:05")
        time_str = (
            f"Ano {current_year} - Dia {current_day} - {current_hour:02d}:{current_minute:02d}"
        )

        self.clock_label.config(text=time_str)

    def update_dynamic_visuals(self):
        for v in self.simulator.vehicles:
            vehicle_tag = f"vehicle_{v.id}"
            new_x, new_y = self._world_to_canvas(*v.map_coordinates)
            self.canvas.coords(vehicle_tag, new_x, new_y)
        self._draw_requests()
        self._draw_station_overlays()

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
        canvas_y = (world_y * self.zoom) + self.offset_y
        return canvas_x, canvas_y

    def _canvas_to_world(self, canvas_x, canvas_y):
        world_x = (canvas_x - self.offset_x) / self.zoom
        world_y = (canvas_y - self.offset_y) / self.zoom
        return world_x, world_y

    def redraw_full_canvas(self):
        if not self.simulator.map:
            return

        self.canvas.delete("all")

        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        # Static
        self._draw_edges(c_width, c_height, margin)
        self._draw_nodes(c_width, c_height, margin)

        # Dinamic
        self._draw_requests()
        self._draw_vehicles()

        # Debug
        self.canvas.create_text(
            10,
            10,
            anchor=tk.NW,
            fill=self.DEBUG_TEXT_COLOR,
            text=f"Zoom: {self.zoom:.2f} | Offset: ({self.offset_x:.0f}, {self.offset_y:.0f})",
        )

    def _draw_edges(self, c_width, c_height, margin):
        for start_node, vizinhos in self.simulator.map.adj.items():
            x1, y1 = self._world_to_canvas(*start_node.position)
            
            for end_node in vizinhos:
                if id(start_node) < id(end_node):
                    x2, y2 = self._world_to_canvas(*end_node.position)
                    
                    if (max(x1, x2) < -margin or
                        min(x1, x2) > c_width + margin or
                        max(y1, y2) < -margin or
                        min(y1, y2) > c_height + margin):
                        continue

                    self.canvas.create_line(
                        x1, y1, x2, y2, fill=self.EDGE_COLOR, width=1, tags=("aresta",)
                    )

    def _draw_nodes(self, c_width, c_height, margin):
        sprite_gas = self.sprite_cache["gas"]
        sprite_ev = self.sprite_cache["ev"]
        # overlay_radius = self.SPRITE_SIZE_PX / 2.5 # No longer needed here

        for node in self.simulator.map.nos:
            x, y = self._world_to_canvas(*node.position)
            if (x < -margin or x > c_width + margin or
                y < -margin or y > c_height + margin):
                continue

            # Draw station
            if node.gas_pumps > 0:
                self.canvas.create_image(x, y, image=sprite_gas, tags=("no", "posto_gas"))
            
            elif node.energy_chargers > 0:
                self.canvas.create_image(x, y, image=sprite_ev, tags=("no", "posto_ev"))

    def _draw_station_overlays(self):
        # Delete all old crosses
        self.canvas.delete("falha_overlay")

        overlay_radius = self.SPRITE_SIZE_PX / 2.5
        
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        for node in self.simulator.map.nos:
            if not node.is_available:
                if node.gas_pumps > 0 or node.energy_chargers > 0:
                    x, y = self._world_to_canvas(*node.position)

                    if (x < -margin or x > c_width + margin or
                        y < -margin or y > c_height + margin):
                        continue 

                    # Draw the cross
                    self.canvas.create_line(
                        x - overlay_radius, y - overlay_radius, x + overlay_radius, y + overlay_radius,
                        fill="red", width=4, tags=("no", "falha_overlay"),
                    )
                    self.canvas.create_line(
                        x - overlay_radius, y + overlay_radius, x + overlay_radius, y - overlay_radius,
                        fill="red", width=4, tags=("no", "falha_overlay"),
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


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApplication(root)
    root.mainloop()
