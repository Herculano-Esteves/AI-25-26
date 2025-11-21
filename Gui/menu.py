import tkinter as tk
from tkinter import ttk
from Simulation.request_simulation import PlanningConfig, set_selected_algorithm

class MenuView:
    def __init__(self, parent, simulator, speed_var):
        self.parent = parent
        self.simulator = simulator
        self.speed_var = speed_var
        
        self.stats_labels = {}
        
        self.frame = ttk.Frame(self.parent, width=450)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        self._create_vehicle_tab()
        self._create_request_tab()
        self._create_metrics_tab()
        self._create_config_tab()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _create_vehicle_tab(self):
        vehicle_tab = ttk.Frame(self.notebook)
        self.notebook.add(vehicle_tab, text="Frota")

        cols = ("id", "status", "autonomy", "request", "motor", "capacidade", 
                "co2", "station_time", "ocup_atual", "ocup_media", "avarias")
        self.vehicle_tree = ttk.Treeview(vehicle_tab, columns=cols, show="headings")

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

        req_scrollbar = ttk.Scrollbar(request_tab, orient=tk.VERTICAL, command=self.request_tree.yview)
        self.request_tree.configure(yscrollcommand=req_scrollbar.set)
        req_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.request_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_metrics_tab(self):
        stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(stats_tab, text="Métricas")

        stats_label_frame = ttk.Frame(stats_tab)
        stats_label_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        curr_row = 0

        def add_stat_row(key, label_text, init_val, header=False):
            nonlocal curr_row
            if header:
                lbl = ttk.Label(stats_label_frame, text=label_text, font=("Arial", 11, "bold"))
                lbl.grid(row=curr_row, column=0, columnspan=2, sticky=tk.W, pady=(10 if curr_row > 0 else 0, 5))
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

        add_stat_row("h2", "Desempenho Financeiro", "", True)
        add_stat_row("total_revenue", "Receita Total:", "€0.00")
        add_stat_row("total_cost", "Custo Op. Total:", "€0.00")
        add_stat_row("total_profit", "Lucro Líquido:", "€0.00")

        add_stat_row("h3", "Eficiência Operacional", "", True)
        add_stat_row("total_requests", "Pedidos (Ok/Fail):", "0 / 0")
        add_stat_row("timeout_cancels", "Cancelados (Timeout):", "0")
        add_stat_row("kms_empty", "Km Vazios (%):", "0%")
        add_stat_row("kms_empty_ev", "Km Vazios EV (%):", "0%")
        add_stat_row("kms_empty_gas", "Km Vazios Gas (%):", "0%")
        add_stat_row("total_co2", "Emissões CO2:", "0.00 kg")
        add_stat_row("loss_time_ev_gas", "Perda Tempo (EV vs Gas):", "0.0m vs 0.0m")

        add_stat_row("h4", "Tempo de Serviço (Minutos)", "", True)
        add_stat_row("avg_wait_time", "Espera Média (Recolha):", "0.0 min")
        add_stat_row("range_wait_time", "Espera [Mín - Máx]:", "0.0 - 0.0")
        add_stat_row("avg_trip_time", "Viagem Média (Entrega):", "0.0 min")
        add_stat_row("range_trip_time", "Viagem [Mín - Máx]:", "0.0 - 0.0")

    def _create_config_tab(self):
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

        ttk.Label(inner_frame, text="Controlo da Simulação", font=("Arial", 12, "bold")).pack(pady=(10, 5), anchor=tk.W, padx=5)

        speed_frame = ttk.LabelFrame(inner_frame, text="Velocidade do Tempo")
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        self.speed_scale = tk.Scale(
            speed_frame, from_=0.1, to=10.0, orient=tk.HORIZONTAL,
            variable=self.speed_var, resolution=0.1, label="Multiplicador (x)"
        )
        self.speed_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # Algorithm Selection
        algo_frame = ttk.LabelFrame(inner_frame, text="Algoritmo de Rota")
        algo_frame.pack(fill=tk.X, padx=10, pady=5)
        
        algo_options = ["A* (A-Star)", "BFS (Breadth-First)", "Greedy (Best-First)"]
        self.algo_combo = ttk.Combobox(algo_frame, values=algo_options, state="readonly")
        self.algo_combo.set("A* (A-Star)")
        self.algo_combo.pack(fill=tk.X, padx=5, pady=5)
        
        def on_algo_change(event):
            selection = self.algo_combo.get()
            key = 'astar'
            if "BFS" in selection:
                key = 'bfs'
            elif "Greedy" in selection:
                key = 'greedy'
            set_selected_algorithm(key)
            
        self.algo_combo.bind("<<ComboboxSelected>>", on_algo_change)

        ttk.Label(inner_frame, text="Pesos do Planeamento (Ao Vivo)", font=("Arial", 12, "bold")).pack(pady=(15, 5), anchor=tk.W, padx=5)

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

            scale = tk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, resolution=resolution, command=on_change)
            scale.set(current_val)
            scale.pack(fill=tk.X)

        create_config_slider("Peso: Tempo Viagem", "WEIGHT_TIME", 0.1, 10.0, 0.1)
        create_config_slider("Peso: Prioridade", "WEIGHT_PRIORITY", 0, 100, 1)
        create_config_slider("Peso: Tempo Espera (Age)", "WEIGHT_AGE", 0.1, 20.0, 0.1)

        ttk.Separator(inner_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        create_config_slider("Penalidade: Eco Mismatch (/km)", "PENALTY_ENV_MISMATCH_PER_KM", 0, 100, 1)
        create_config_slider("Penalidade: Lugar Vazio", "PENALTY_UNUSED_SEAT", 0, 20, 1)
        create_config_slider("Penalidade: Risco Bateria", "WEIGHT_BATTERY_RISK", 0, 100, 1)

        ttk.Separator(inner_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        create_config_slider("Peso: Custo Oportunidade (EV)", "WEIGHT_LOST_OPPORTUNITY", 0, 200, 5)

    def update_stats(self):
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
                v.id, status_str, autonomy_str, request_id,
                v.motor.name[0:4], v.passenger_capacity,
                f"{v.co2_emitted:.2f}", f"{v.total_station_time:.1f}",
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
                req_list.append((
                    r.id, status_code, f"{r.start_node.position}", f"{r.end_node.position}",
                    r.passenger_capacity, pref_str
                ))

        add_reqs(self.simulator.requests, "Pendente")
        add_reqs(self.simulator.requests_to_pickup, "Apanhar")
        add_reqs(self.simulator.requests_to_dropoff, "Viagem")

        req_list.sort(key=lambda x: x[0])
        for r in req_list:
            self.request_tree.insert("", tk.END, values=r)

        self._update_metrics_values()

    def _update_metrics_values(self):
        stats = self.simulator.stats
        labels = self.stats_labels

        labels["step_cost"].config(text=f"€{stats.step_operational_cost:,.2f}")
        labels["step_revenue"].config(text=f"€{stats.step_revenue_generated:,.2f}")
        labels["step_pending_req"].config(text=f"{stats.step_pending_requests}")

        busy_vs = stats.step_vehicles_on_trip + stats.step_vehicles_charging + stats.step_vehicles_unavailable
        labels["step_vehicles_busy"].config(text=f"{busy_vs}")

        labels["total_revenue"].config(text=f"€{stats.total_revenue_generated:,.2f}")
        labels["total_cost"].config(text=f"€{stats.total_operational_cost:,.2f}")
        profit = stats.total_revenue_generated - stats.total_operational_cost
        labels["total_profit"].config(text=f"€{profit:,.2f}")

        labels["total_requests"].config(text=f"{stats.total_requests_completed} / {stats.total_requests_failed}")
        labels["timeout_cancels"].config(text=f"{stats.total_requests_cancelled_timeout}")

        empty_ratio = (stats.total_kms_driven_empty / stats.total_kms_driven * 100) if stats.total_kms_driven > 0 else 0.0
        labels["kms_empty"].config(text=f"{empty_ratio:.1f}%")

        ev_empty_ratio = (stats.total_kms_driven_empty_ev / stats.total_kms_driven_ev * 100) if stats.total_kms_driven_ev > 0 else 0.0
        labels["kms_empty_ev"].config(text=f"{ev_empty_ratio:.1f}%")

        gas_empty_ratio = (stats.total_kms_driven_empty_gas / stats.total_kms_driven_gas * 100) if stats.total_kms_driven_gas > 0 else 0.0
        labels["kms_empty_gas"].config(text=f"{gas_empty_ratio:.1f}%")

        labels["total_co2"].config(text=f"{stats.total_co2_emitted:.2f} kg")
        labels["loss_time_ev_gas"].config(text=f"{stats.total_station_time_ev:.1f}m vs {stats.total_station_time_gas:.1f}m")

        avg_wait = (stats.total_wait_time_for_pickup / stats.total_requests_picked_up) if stats.total_requests_picked_up > 0 else 0.0
        labels["avg_wait_time"].config(text=f"{avg_wait:.1f} min")

        min_wait = 0.0 if stats.min_wait_time == float("inf") else stats.min_wait_time
        labels["range_wait_time"].config(text=f"{min_wait:.1f} - {stats.max_wait_time:.1f}")

        avg_trip = (stats.total_time_for_completed_requests / stats.total_requests_completed) if stats.total_requests_completed > 0 else 0.0
        labels["avg_trip_time"].config(text=f"{avg_trip:.1f} min")

        min_trip = 0.0 if stats.min_total_trip_time == float("inf") else stats.min_total_trip_time
        labels["range_trip_time"].config(text=f"{min_trip:.1f} - {stats.max_total_trip_time:.1f}")
