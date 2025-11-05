import tkinter as tk
from tkinter import ttk

from models import Motor
from simulator import Simulator

import os
from PIL import Image, ImageTk


class MapApplication:
    # GUI constants
    TICK_RATE_MS = 40  # 25 FPS

    # Navigation constants
    ZOOM_IN_FACTOR = 1.2  # Zoom-in
    ZOOM_OUT_FACTOR = 1 / 1.2  # Zoom-out
    PADDING_RESET = 40  # Extra pixels on reset

    # Visual constants
    BG_COLOR = "#2c2c2c"
    EDGE_COLOR = "#4a4a4a"
    NODE_COLOR = "lightblue"
    GAS_COLOR = "orange"
    EV_COLOR = "limegreen"
    REQUEST_COLOR = "deep sky blue"
    REQUEST_ACCEPTED_COLOR = "yellow"
    REQUEST_DESTINATION_COLOR = "magenta"
    VEHICLE_EV_COLOR = "green"
    VEHICLE_GAS_COLOR = "red"
    DEBUG_TEXT_COLOR = "yellow"

    # Drawing constants
    NODE_RADIUS = 4
    SPRITE_SIZE_PX = 24
    REQUEST_FONT = ("Arial", 20)

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Frota")
        self.root.geometry("1000x1000")

        # Saves images references
        self.sprite_cache = {}
        try:
            self._load_sprites()
        except Exception as e:
            print(f"Erro fatal ao carregar imagens: {e}")
            print(
                "Verifique se a pasta 'images' existe e contém todos os PNGs necessários."
            )
            root.destroy()
            return

        self.simulator = Simulator()

        self.simulation_running = False

        # Camera variables
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 20.0  # Pixels per world unit

        # Slide variables
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_offset_x = 0
        self._drag_start_offset_y = 0

        # Iterface setup
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

        # Canvas frame
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Tkinter
        self.canvas = tk.Canvas(canvas_frame, bg=self.BG_COLOR, cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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
        self.reset_view()

    def reset_view(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            self.root.after(100, self.reset_view)
            return

        usable_w = canvas_w - (2 * self.PADDING_RESET)
        usable_h = canvas_h - (2 * self.PADDING_RESET)

        map_world_w = (
            self.simulator.MAP_WIDTH - 1 if self.simulator.MAP_WIDTH > 1 else 1
        )
        map_world_h = (
            self.simulator.MAP_HEIGHT - 1 if self.simulator.MAP_HEIGHT > 1 else 1
        )

        scale_x = usable_w / map_world_w
        scale_y = usable_h / map_world_h
        self.zoom = min(scale_x, scale_y)

        map_pixel_w = map_world_w * self.zoom
        map_pixel_h = map_world_h * self.zoom
        self.offset_x = (canvas_w - map_pixel_w) / 2
        self.offset_y = (canvas_h - map_pixel_h) / 2

        self.redraw_full_canvas()

    def start_simulation(self):
        # Simulation loop starter
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
        # Pause simulation loop
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
        self.root.after(self.TICK_RATE_MS, self._simulation_gui_loop)  # Next frame

    def update_dynamic_visuals(self):
        for v in self.simulator.vehicles:
            vehicle_tag = f"vehicle_{v.id}"
            new_x, new_y = self._world_to_canvas(*v.map_coordinates)
            self.canvas.coords(vehicle_tag, new_x, new_y)
        self._draw_requests()

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
        canvas_x_after, canvas_y_after = self._world_to_canvas(
            world_x_before, world_y_before
        )
        self.offset_x += event.x - canvas_x_after
        self.offset_y += event.y - canvas_y_after
        self.redraw_full_canvas()

    def _on_drag_start(self, event):
        self.canvas.config(cursor="fleur")
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_start_offset_x = self.offset_x
        self._drag_start_offset_y = self.offset_y

    def _on_drag_motion(self, event):
        delta_x = event.x - self._drag_start_x
        delta_y = event.y - self._drag_start_y
        self.offset_x = self._drag_start_offset_x + delta_x
        self.offset_y = self._drag_start_offset_y + delta_y
        self.redraw_full_canvas()

    def _on_drag_end(self, event):
        self.canvas.config(cursor="crosshair")  # Restore cursor

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

        # Static
        self._draw_edges()
        self._draw_nodes()

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

    def _draw_edges(self):
        for start_node, vizinhos in self.simulator.map.adj.items():
            x1, y1 = self._world_to_canvas(*start_node.position)
            for end_node in vizinhos:
                if start_node == end_node:
                    continue
                x2, y2 = self._world_to_canvas(*end_node.position)
                self.canvas.create_line(
                    x1, y1, x2, y2, fill=self.EDGE_COLOR, width=1, tags=("aresta",)
                )

    def _draw_nodes(self):
        sprite_gas = self.sprite_cache["gas"]
        sprite_ev = self.sprite_cache["ev"]
        node_radius = self.NODE_RADIUS

        for node in self.simulator.map.nos:
            x, y = self._world_to_canvas(*node.position)

            if node.gas_pumps > 0:
                self.canvas.create_image(
                    x, y, image=sprite_gas, tags=("no", "posto_gas")
                )
            elif node.energy_chargers > 0:
                self.canvas.create_image(x, y, image=sprite_ev, tags=("no", "posto_ev"))
            else:
                self.canvas.create_oval(
                    x - node_radius,
                    y - node_radius,
                    x + node_radius,
                    y + node_radius,
                    fill=self.NODE_COLOR,
                    outline=self.EDGE_COLOR,
                    tags=("no", "no_normal"),
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
