import tkinter as tk
from tkinter import ttk
from Simulation.request_simulation import (
    set_selected_algorithm,
    set_selected_assignment_algorithm,
    set_selected_cost_estimation_algorithm,
)
from Simulation.simulation_config import PlanningConfig
from Simulation.benchmark import BenchmarkRunner


class MenuView:
    """Painel lateral com tabs de frota, pedidos, métricas e configurações."""

    def __init__(self, parent, simulator, speed_var):
        self.parent = parent
        self.simulator = simulator
        self.speed_var = speed_var
        self.render_map_var = tk.BooleanVar(value=True)

        self.stats_labels = {}
        self.benchmark_runner = None

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
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Frota")

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
        self.vehicle_tree = ttk.Treeview(tab, columns=cols, show="headings")

        headers = {
            "id": ("ID", 35),
            "status": ("Estado", 85),
            "autonomy": ("Aut.", 50),
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

        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.vehicle_tree.yview)
        self.vehicle_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vehicle_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_request_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Pedidos")

        cols = ("id", "status", "from", "to", "pax", "pref")
        self.request_tree = ttk.Treeview(tab, columns=cols, show="headings")

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

        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.request_tree.yview)
        self.request_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.request_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _create_metrics_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Métricas")

        container = ttk.Frame(tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0

        def add_row(key, label, init="", header=False):
            nonlocal row
            if header:
                lbl = ttk.Label(container, text=label, font=("Arial", 11, "bold"))
                lbl.grid(
                    row=row, column=0, columnspan=2, sticky=tk.W, pady=(10 if row > 0 else 0, 5)
                )
                self.stats_labels[key] = lbl
            else:
                ttk.Label(container, text=label).grid(row=row, column=0, sticky=tk.W)
                lbl = ttk.Label(container, text=init, font=("Arial", 10))
                lbl.grid(row=row, column=1, sticky=tk.W, padx=5)
                self.stats_labels[key] = lbl
            row += 1

        add_row("h1", "Em Tempo Real (Snapshot)", header=True)
        add_row("step_cost", "Custo Op. Instantâneo:", "€0.00")
        add_row("step_revenue", "Receita Instantânea:", "€0.00")
        add_row("step_pending_req", "Pendentes na Fila:", "0")
        add_row("step_vehicles_busy", "Veículos Ativos:", "0")

        add_row("h2", "Desempenho Financeiro", header=True)
        add_row("total_revenue", "Receita Total:", "€0.00")
        add_row("total_cost", "Custo Op. Total:", "€0.00")
        add_row("total_profit", "Lucro Líquido:", "€0.00")

        add_row("h3", "Eficiência Operacional", header=True)
        add_row("total_requests", "Pedidos (Ok/Fail):", "0 / 0")
        add_row("timeout_cancels", "Cancelados (Timeout):", "0")
        add_row("kms_empty", "Km Vazios (%):", "0%")
        add_row("kms_empty_ev", "Km Vazios EV (%):", "0%")
        add_row("kms_empty_gas", "Km Vazios Gas (%):", "0%")
        add_row("total_co2", "Emissões CO2:", "0.00 kg")
        add_row("loss_time_ev_gas", "Perda Tempo (EV vs Gas):", "0.0m vs 0.0m")

        add_row("h4", "Tempo de Serviço (Minutos)", header=True)
        add_row("avg_wait_time", "Espera Média (Recolha):", "0.0 min")
        add_row("range_wait_time", "Espera [Mín - Máx]:", "0.0 - 0.0")
        add_row("avg_trip_time", "Viagem Média (Entrega):", "0.0 min")
        add_row("range_trip_time", "Viagem [Mín - Máx]:", "0.0 - 0.0")

    def _create_config_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Configurações")

        scroll = ttk.Scrollbar(tab)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        canvas = tk.Canvas(tab, yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=canvas.yview)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        ttk.Label(inner, text="Controlo da Simulação", font=("Arial", 12, "bold")).pack(
            pady=(10, 5), anchor=tk.W, padx=5
        )

        # Velocidade
        speed_frame = ttk.LabelFrame(inner, text="Velocidade do Tempo")
        speed_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Scale(
            speed_frame,
            from_=0.1,
            to=10.0,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            resolution=0.1,
            label="Multiplicador (x)",
        ).pack(fill=tk.X, padx=5, pady=5)

        # Algoritmo de rota
        algo_frame = ttk.LabelFrame(inner, text="Algoritmo de Rota")
        algo_frame.pack(fill=tk.X, padx=10, pady=5)
        self.algo_combo = ttk.Combobox(
            algo_frame,
            values=["A* (Informado)", "BFS (Não Informado)", "Greedy (Informado)"],
            state="readonly",
        )
        self.algo_combo.set("A* (Informado)")
        self.algo_combo.pack(fill=tk.X, padx=5, pady=5)
        self.algo_combo.bind("<<ComboboxSelected>>", self._on_algo_change)

        # Algoritmo de atribuição
        assign_frame = ttk.LabelFrame(inner, text="Algoritmo de Atribuição")
        assign_frame.pack(fill=tk.X, padx=10, pady=5)
        self.assign_combo = ttk.Combobox(
            assign_frame,
            values=["Simulated Annealing", "Greedy", "Hill Climbing"],
            state="readonly",
        )
        self.assign_combo.set("Simulated Annealing")
        self.assign_combo.pack(fill=tk.X, padx=5, pady=5)
        self.assign_combo.bind("<<ComboboxSelected>>", self._on_assign_change)

        # Estimativa de custo
        cost_frame = ttk.LabelFrame(inner, text="Estimativa de Custo (Atribuição)")
        cost_frame.pack(fill=tk.X, padx=10, pady=5)
        self.cost_est_combo = ttk.Combobox(
            cost_frame, values=["Distância", "A* (Preciso)"], state="readonly"
        )
        self.cost_est_combo.set("Distância")
        self.cost_est_combo.pack(fill=tk.X, padx=5, pady=5)
        self.cost_est_combo.bind("<<ComboboxSelected>>", self._on_cost_est_change)

        # Benchmark
        bench_frame = ttk.LabelFrame(inner, text="Benchmark Automático")
        bench_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Checkbutton(
            bench_frame, text="Renderizar Mapa (Mais lento)", variable=self.render_map_var
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.lbl_bench_status = ttk.Label(bench_frame, text="Pronto", font=("Arial", 9, "italic"))
        self.lbl_bench_status.pack(anchor=tk.W, padx=5, pady=2)
        self.btn_bench = ttk.Button(
            bench_frame, text="Iniciar Benchmark (9 Testes)", command=self.start_benchmark_ui
        )
        self.btn_bench.pack(fill=tk.X, padx=5, pady=5)

    def _on_algo_change(self, event):
        sel = self.algo_combo.get()
        key = "bfs" if "BFS" in sel else "greedy" if "Greedy" in sel else "astar"
        set_selected_algorithm(key)

    def _on_assign_change(self, event):
        set_selected_assignment_algorithm(self.assign_combo.get())

    def _on_cost_est_change(self, event):
        sel = self.cost_est_combo.get()
        set_selected_cost_estimation_algorithm("astar" if "A*" in sel else "heuristic")

    def start_benchmark_ui(self):
        if self.benchmark_runner and self.benchmark_runner.is_running:
            return
        self.btn_bench.config(state=tk.DISABLED)
        self.lbl_bench_status.config(text="A iniciar...")

        def on_update(msg):
            self.frame.after(0, lambda: self.lbl_bench_status.config(text=msg))

        def on_complete():
            self.frame.after(0, self._on_benchmark_complete)

        self.benchmark_runner = BenchmarkRunner(on_update, on_complete)
        self.benchmark_runner.start_benchmark()

    def _on_benchmark_complete(self):
        self.lbl_bench_status.config(text="Benchmark Concluído! Ver benchmark_results.json")
        self.btn_bench.config(state=tk.NORMAL)
        print("Benchmark finished.")
        self.simulator.reset_simulation_state()

    def update_stats(self):
        if not self.simulator:
            return
        self._update_vehicle_tree()
        self._update_request_tree()
        self._update_metrics_values()

    def _update_vehicle_tree(self):
        self.vehicle_tree.delete(*self.vehicle_tree.get_children())
        for v in self.simulator.vehicles:
            status = v.condition.name.replace("_", " ").title()
            if status == "Unavailable":
                status = "Quebrado"
            ocup_atual = (
                f"{(v.request.passenger_capacity / v.passenger_capacity * 100):.0f}%"
                if v.request
                else "0%"
            )
            ocup_media = (
                f"{(v.sum_occupancy / v.total_trips * 100):.0f}%" if v.total_trips > 0 else "0%"
            )
            self.vehicle_tree.insert(
                "",
                tk.END,
                values=(
                    v.id,
                    status,
                    f"{v.remaining_km:.0f}/{v.max_km:.0f}",
                    v.request.id if v.request else "---",
                    v.motor.name[:4],
                    v.passenger_capacity,
                    f"{v.co2_emitted:.2f}",
                    f"{v.total_station_time:.1f}",
                    ocup_atual,
                    ocup_media,
                    v.times_borken,
                ),
            )

    def _update_request_tree(self):
        self.request_tree.delete(*self.request_tree.get_children())
        reqs = []

        def add(lst, status):
            for r in lst:
                reqs.append(
                    (
                        r.id,
                        status,
                        f"{r.start_node.position}",
                        f"{r.end_node.position}",
                        r.passenger_capacity,
                        "Sim" if r.environmental_preference else "-",
                    )
                )

        add(self.simulator.requests, "Pendente")
        add(self.simulator.requests_to_pickup, "Apanhar")
        add(self.simulator.requests_to_dropoff, "Viagem")
        for r in sorted(reqs, key=lambda x: x[0]):
            self.request_tree.insert("", tk.END, values=r)

    def _update_metrics_values(self):
        s = self.simulator.stats
        lbl = self.stats_labels

        lbl["step_cost"].config(text=f"€{s.step_operational_cost:,.2f}")
        lbl["step_revenue"].config(text=f"€{s.step_revenue_generated:,.2f}")
        lbl["step_pending_req"].config(text=str(s.step_pending_requests))
        busy = s.step_vehicles_on_trip + s.step_vehicles_charging + s.step_vehicles_unavailable
        lbl["step_vehicles_busy"].config(text=str(busy))

        lbl["total_revenue"].config(text=f"€{s.total_revenue_generated:,.2f}")
        lbl["total_cost"].config(text=f"€{s.total_operational_cost:,.2f}")
        lbl["total_profit"].config(
            text=f"€{s.total_revenue_generated - s.total_operational_cost:,.2f}"
        )

        lbl["total_requests"].config(
            text=f"{s.total_requests_completed} / {s.total_requests_failed}"
        )
        lbl["timeout_cancels"].config(text=str(s.total_requests_cancelled_timeout))

        empty = (
            (s.total_kms_driven_empty / s.total_kms_driven * 100) if s.total_kms_driven > 0 else 0
        )
        lbl["kms_empty"].config(text=f"{empty:.1f}%")
        ev_empty = (
            (s.total_kms_driven_empty_ev / s.total_kms_driven_ev * 100)
            if s.total_kms_driven_ev > 0
            else 0
        )
        lbl["kms_empty_ev"].config(text=f"{ev_empty:.1f}%")
        gas_empty = (
            (s.total_kms_driven_empty_gas / s.total_kms_driven_gas * 100)
            if s.total_kms_driven_gas > 0
            else 0
        )
        lbl["kms_empty_gas"].config(text=f"{gas_empty:.1f}%")

        lbl["total_co2"].config(text=f"{s.total_co2_emitted:.2f} kg")
        lbl["loss_time_ev_gas"].config(
            text=f"{s.total_station_time_ev:.1f}m vs {s.total_station_time_gas:.1f}m"
        )

        avg_wait = (
            s.total_wait_time_for_pickup / s.total_requests_picked_up
            if s.total_requests_picked_up > 0
            else 0
        )
        lbl["avg_wait_time"].config(text=f"{avg_wait:.1f} min")
        min_wait = 0 if s.min_wait_time == float("inf") else s.min_wait_time
        lbl["range_wait_time"].config(text=f"{min_wait:.1f} - {s.max_wait_time:.1f}")

        avg_trip = (
            s.total_time_for_completed_requests / s.total_requests_completed
            if s.total_requests_completed > 0
            else 0
        )
        lbl["avg_trip_time"].config(text=f"{avg_trip:.1f} min")
        min_trip = 0 if s.min_total_trip_time == float("inf") else s.min_total_trip_time
        lbl["range_trip_time"].config(text=f"{min_trip:.1f} - {s.max_total_trip_time:.1f}")
