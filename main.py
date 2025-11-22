import tkinter as tk
from tkinter import ttk
import time
from Simulation.simulator import Simulator
from Gui.map import MapView
from Gui.menu import MenuView


class MapApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota - Painel de Controlo")
        self.root.geometry("1600x1000")

        self.simulator = Simulator()
        self.simulation_running = False

        # FPS Tracking
        self.last_frame_time = time.time()
        self.fps_avg = 0.0

        # Speed Control Variable
        self.speed_var = tk.DoubleVar(value=1.0)

        self._create_interface()

        self.map_view.reset_view()

        # Start the loop immediately, but it will be idle
        self._simulation_gui_loop()

    def _create_interface(self):
        # TOP CONTROL BAR
        control_frame = ttk.LabelFrame(self.root, text="Controlos de Simulação")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        # Buttons Left
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
        self.weather_label = ttk.Label(info_panel, text="--", font=("Arial", 11))
        self.weather_label.pack(side=tk.TOP, anchor="e")

        # FPS Label (Left of the clock)
        self.fps_label = ttk.Label(control_frame, text="FPS: 0", font=("Consolas", 9))
        self.fps_label.pack(side=tk.RIGHT, padx=20)

        # MAIN SPLIT VIEW
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Map Area
        self.map_view = MapView(self.main_paned_window, self.simulator)
        self.main_paned_window.add(self.map_view.frame, weight=4)

        # Stats/Config Panel
        self.menu_view = MenuView(self.main_paned_window, self.simulator, self.speed_var)
        self.main_paned_window.add(self.menu_view.frame, weight=1)

    def setup_new_map(self):
        print("A gerar novo map...")
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

        self.btn_reset_view.config(state=tk.DISABLED)

    def stop_simulation(self):
        print("A parar simulação...")
        self.simulation_running = False

        self.btn_start_sim.config(state=tk.NORMAL)
        self.btn_stop_sim.config(state=tk.DISABLED)
        self.btn_generate_map.config(state=tk.NORMAL)
        self.btn_reset_view.config(state=tk.NORMAL)

    def _simulation_gui_loop(self):
        # Check if benchmark is running
        is_benchmarking = (
            self.menu_view.benchmark_runner is not None
            and self.menu_view.benchmark_runner.is_running
        )

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

        # Step Simulation (Only if NOT benchmarking, as benchmark has its own loop)
        if not is_benchmarking and self.simulation_running:
            self.simulator.simulation_step(time_multiplier=speed_mult)

        # Update Visuals
        # Check if rendering is enabled
        if self.menu_view.render_map_var.get():
            self.map_view.update_dynamic_visuals()

        self.menu_view.update_stats()
        self._update_clock()

        self.root.after(50, self._simulation_gui_loop)

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


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApplication(root)
    root.mainloop()
