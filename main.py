import tkinter as tk
from tkinter import ttk
import time
from Simulation.simulator import Simulator
from Gui.map import MapView
from Gui.menu import MenuView


class MapApplication:
    """Aplicação principal do simulador de frota."""

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota - Painel de Controlo")
        self.root.geometry("1600x1000")

        self.simulator = Simulator()
        self.simulation_running = False
        self.last_frame_time = time.time()
        self.fps_avg = 0.0
        self.speed_var = tk.DoubleVar(value=1.0)

        self._create_interface()
        self.map_view.reset_view()
        self._simulation_gui_loop()

    def _create_interface(self):
        # Barra de controlo
        control_frame = ttk.LabelFrame(self.root, text="Controlos de Simulação")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, padx=10, pady=5)

        self.btn_generate_map = ttk.Button(
            btn_frame, text="Reiniciar Simulação", command=self.setup_new_map
        )
        self.btn_generate_map.pack(side=tk.LEFT, padx=2)

        self.btn_reset_view = ttk.Button(
            btn_frame, text="Resetar View", command=lambda: self.map_view.reset_view()
        )
        self.btn_reset_view.pack(side=tk.LEFT, padx=2)

        self.btn_start_sim = ttk.Button(btn_frame, text="▶ Iniciar", command=self.start_simulation)
        self.btn_start_sim.pack(side=tk.LEFT, padx=2)

        self.btn_stop_sim = ttk.Button(
            btn_frame, text="⏹ Parar", command=self.stop_simulation, state=tk.DISABLED
        )
        self.btn_stop_sim.pack(side=tk.LEFT, padx=2)

        # Painel de info (direita)
        info_panel = ttk.Frame(control_frame)
        info_panel.pack(side=tk.RIGHT, padx=15, pady=2)

        self.date_label = ttk.Label(
            info_panel, text="Ano 0 - Dia 0", font=("Arial", 9), foreground="#666666"
        )
        self.date_label.pack(side=tk.TOP, anchor="e")

        self.time_label = ttk.Label(
            info_panel, text="08:00", font=("Arial", 22, "bold"), foreground="#000000"
        )
        self.time_label.pack(side=tk.TOP, anchor="e")

        self.weather_label = ttk.Label(info_panel, text="--", font=("Arial", 11))
        self.weather_label.pack(side=tk.TOP, anchor="e")

        self.fps_label = ttk.Label(control_frame, text="FPS: 0", font=("Consolas", 9))
        self.fps_label.pack(side=tk.RIGHT, padx=20)

        # Vista principal
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.map_view = MapView(self.main_paned_window, self.simulator)
        self.main_paned_window.add(self.map_view.frame, weight=4)

        self.menu_view = MenuView(self.main_paned_window, self.simulator, self.speed_var)
        self.main_paned_window.add(self.menu_view.frame, weight=1)

    def setup_new_map(self):
        print("A gerar novo mapa...")
        self.simulator.setup_new_map()
        self._update_clock()
        self.map_view.reset_view()

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

    def stop_simulation(self):
        print("A parar simulação...")
        self.simulation_running = False

        self.btn_start_sim.config(state=tk.NORMAL)
        self.btn_stop_sim.config(state=tk.DISABLED)
        self.btn_generate_map.config(state=tk.NORMAL)
        self.btn_reset_view.config(state=tk.NORMAL)

    def _simulation_gui_loop(self):
        is_benchmarking = (
            self.menu_view.benchmark_runner is not None
            and self.menu_view.benchmark_runner.is_running
        )

        # FPS - contar frames por segundo
        now = time.time()
        self.frame_count = getattr(self, "frame_count", 0) + 1
        self.fps_last_update = getattr(self, "fps_last_update", now)

        elapsed = now - self.fps_last_update
        if elapsed >= 1.0:
            fps = self.frame_count / elapsed
            self.fps_label.config(text=f"FPS: {fps:.1f}")
            self.frame_count = 0
            self.fps_last_update = now

        if not is_benchmarking and self.simulation_running:
            self.simulator.simulation_step(time_multiplier=self.speed_var.get())

        if self.menu_view.render_map_var.get():
            self.map_view.update_dynamic_visuals()

        self.menu_view.update_stats()
        self._update_clock()
        self.root.after(50, self._simulation_gui_loop)

    def _update_clock(self):
        day, hour, minute, year = self.simulator.get_current_time_of_day()

        self.date_label.config(text=f"Ano {year} - Dia {day}")
        self.time_label.config(text=f"{hour:02d}:{minute:02d}")

        if hasattr(self.simulator, "traffic_manager"):
            cond = self.simulator.traffic_manager.current_weather_condition
            icons = {"Limpo": "☀", "Nublado": "☁", "Chuva": "🌧", "Tempestade": "⛈"}
            colors = {
                "Limpo": "#000000",
                "Nublado": "#555555",
                "Chuva": "#0066cc",
                "Tempestade": "#cc0000",
            }
            icon = icons.get(cond, "☀")
            color = colors.get(cond, "#000000")
            self.weather_label.config(text=f"{icon} {cond}", foreground=color)


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApplication(root)
    root.mainloop()
