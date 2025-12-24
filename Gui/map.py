import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk
from models.vehicle import Motor


class MapView:
    # GUI constants
    TICK_RATE_MS = 50

    # Navigation constants
    ZOOM_IN_FACTOR = 1.2
    ZOOM_OUT_FACTOR = 1 / 1.2
    PADDING_RESET = 40
    ZOOM_THRESHOLD_TRAFFIC = 10000.0

    # Visual constants
    BG_COLOR = "#2c2c2c"
    EDGE_COLOR = "#4a4a4a"
    NODE_COLOR = "lightblue"
    REQUEST_ACCEPTED_COLOR = "yellow"
    REQUEST_DESTINATION_COLOR = "magenta"
    DEBUG_TEXT_COLOR = "yellow"

    # Drawing constants
    SPRITE_SIZE_PX = 22
    REQUEST_FONT = ("Arial", 20)
    KM_PER_DEGREE_LAT = 130

    def __init__(self, parent, simulator):
        self.parent = parent
        self.simulator = simulator

        self.sprite_cache = {}
        self._load_sprites()

        # Camera variables
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 20.0

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_offset_x = 0
        self._drag_start_offset_y = 0
        self._drag_last_x = 0
        self._drag_last_y = 0

        # UI Elements
        self.frame = ttk.Frame(self.parent)
        self.canvas = tk.Canvas(self.frame, bg=self.BG_COLOR, cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._setup_bindings()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _load_sprites(self):
        print("A carregar sprites...")
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
                print(f"Warning: Sprite {filename} not found at {img_path}")
            except Exception as e:
                print(f"Error loading sprite {filename}: {e}")

    def _setup_bindings(self):
        self.canvas.bind("<Button-4>", self._on_zoom)
        self.canvas.bind("<Button-5>", self._on_zoom)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Configure>", self._on_resize)

    def reset_view(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            self.frame.after(100, self.reset_view)
            return

        city_map = getattr(self.simulator, "map", None)
        if city_map and getattr(city_map, "nos", None):
            nodes = list(city_map.nos)
            if nodes:
                lons = [p.position[0] for p in nodes]
                lats = [p.position[1] for p in nodes]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)

                world_w = max_lon - min_lon if max_lon > min_lon else 1.0
                world_h = max_lat - min_lat if max_lat > min_lat else 1.0

                usable_w = canvas_w - (2 * self.PADDING_RESET)
                usable_h = canvas_h - (2 * self.PADDING_RESET)

                scale_x = usable_w / world_w
                scale_y = usable_h / world_h
                self.zoom = min(scale_x, scale_y)

                center_lon = (min_lon + max_lon) / 2.0
                center_lat = (min_lat + max_lat) / 2.0

                self.offset_x = (canvas_w / 2.0) - (center_lon * self.zoom)
                self.offset_y = (canvas_h / 2.0) - (-center_lat * self.zoom)

                self.redraw_full_canvas()
                return

        # Fallback if no map loaded yet
        self.redraw_full_canvas()

    def _on_resize(self, event):
        self.redraw_full_canvas()

    def _on_zoom(self, event):
        zoom_factor = 1.0
        if event.num == 4:
            zoom_factor = self.ZOOM_IN_FACTOR
        elif event.num == 5:
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
        self.canvas.move("all", delta_x, delta_y)

        total_delta_x = event.x - self._drag_start_x
        total_delta_y = event.y - self._drag_start_y
        self.offset_x = self._drag_start_offset_x + total_delta_x
        self.offset_y = self._drag_start_offset_y + total_delta_y

        self._drag_last_x = event.x
        self._drag_last_y = event.y

    def _on_drag_end(self, event):
        self.canvas.config(cursor="crosshair")
        self.redraw_full_canvas()

    def _world_to_canvas(self, world_x, world_y):
        canvas_x = (world_x * self.zoom) + self.offset_x
        canvas_y = (-world_y * self.zoom) + self.offset_y
        return canvas_x, canvas_y

    def _canvas_to_world(self, canvas_x, canvas_y):
        world_x = (canvas_x - self.offset_x) / self.zoom
        world_y = -(canvas_y - self.offset_y) / self.zoom
        return world_x, world_y

    def update_dynamic_visuals(self):
        if not self.simulator:
            return

        for v in self.simulator.vehicles:
            vehicle_tag = f"vehicle_{v.id}"
            new_x, new_y = self._world_to_canvas(*v.map_coordinates)
            self.canvas.coords(vehicle_tag, new_x, new_y)

        self._draw_requests()
        self._draw_vehicles()
        self._draw_hotspots()
        self._draw_station_overlays()

        if self.zoom > self.ZOOM_THRESHOLD_TRAFFIC:
            self.canvas.delete("aresta")
            c_width = self.canvas.winfo_width()
            c_height = self.canvas.winfo_height()
            margin = 100
            self._draw_edges(c_width, c_height, margin)
            self.canvas.tag_lower("aresta")

    def redraw_full_canvas(self):
        if not self.simulator or not self.simulator.map:
            return

        self.canvas.delete("all")
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        self._draw_edges(c_width, c_height, margin)
        self._draw_nodes(c_width, c_height, margin)
        self._draw_hotspots()
        self._draw_station_overlays()
        self._draw_requests()
        self._draw_vehicles()

        # Debug Info
        self.canvas.create_text(
            10,
            10,
            anchor=tk.NW,
            fill=self.DEBUG_TEXT_COLOR,
            text=f"Zoom: {self.zoom:.2f} | Offset: ({self.offset_x:.0f}, {self.offset_y:.0f})",
        )

    def _draw_edges(self, c_width, c_height, margin):
        show_traffic = (self.zoom > self.ZOOM_THRESHOLD_TRAFFIC) and hasattr(
            self.simulator, "traffic_manager"
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
        sprite_gas = self.sprite_cache.get("gas")
        sprite_ev = self.sprite_cache.get("ev")

        all_station_nodes = set()
        if hasattr(self.simulator.map, "gas_stations"):
            all_station_nodes.update(self.simulator.map.gas_stations)
        if hasattr(self.simulator.map, "ev_stations"):
            all_station_nodes.update(self.simulator.map.ev_stations)

        for node in all_station_nodes:
            x, y = self._world_to_canvas(*node.position)
            if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                continue
            
            has_gas = node.gas_pumps > 0
            has_ev = node.energy_chargers > 0
            
            if has_gas and has_ev:
                offset = self.SPRITE_SIZE_PX * 0.6
                if sprite_gas:
                    self.canvas.create_image(
                        x - offset, y, image=sprite_gas, tags=("no", "posto_gas")
                    )
                if sprite_ev:
                    self.canvas.create_image(
                        x + offset, y, image=sprite_ev, tags=("no", "posto_ev")
                    )
            elif has_gas and sprite_gas:
                # Gas-only station: centered
                self.canvas.create_image(x, y, image=sprite_gas, tags=("no", "posto_gas"))
            elif has_ev and sprite_ev:
                # EV-only station: centered
                self.canvas.create_image(x, y, image=sprite_ev, tags=("no", "posto_ev"))

    def _draw_station_overlays(self):
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
        sprite_wait = self.sprite_cache.get("request_wait")
        sprite_accepted = self.sprite_cache.get("request_accepted")

        if sprite_wait:
            for p in self.simulator.requests:
                x, y = self._world_to_canvas(*p.start_node.position)
                self.canvas.create_image(
                    x, y - 10, image=sprite_wait, tags=("request", f"request_{p.id}")
                )

        if sprite_accepted:
            for p in self.simulator.requests_to_pickup:
                x, y = self._world_to_canvas(*p.start_node.position)
                self.canvas.create_image(
                    x, y - 10, image=sprite_accepted, tags=("request", f"request_{p.id}")
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
        sprite_ev = self.sprite_cache.get("carro_ev")
        sprite_gas = self.sprite_cache.get("carro_gas")

        for v in self.simulator.vehicles:
            x, y = self._world_to_canvas(*v.map_coordinates)
            sprite_to_use = sprite_ev if v.motor == Motor.ELECTRIC else sprite_gas
            if sprite_to_use:
                self.canvas.create_image(
                    x, y, image=sprite_to_use, tags=("vehicle", f"vehicle_{v.id}")
                )

    def _draw_hotspots(self):
        if not self.simulator.hotspot_manager:
            return

        self.canvas.delete("hotspot")
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        margin = 100

        for h in self.simulator.hotspot_manager.hotspots:
            x, y = self._world_to_canvas(*h.coordinates)
            radius_pixels = (h.radius_km / self.KM_PER_DEGREE_LAT) * self.zoom

            if x < -margin or x > c_width + margin or y < -margin or y > c_height + margin:
                continue

            outline_color = "green" if h.is_active else "red"
            self.canvas.create_oval(
                x - radius_pixels,
                y - radius_pixels,
                x + radius_pixels,
                y + radius_pixels,
                outline=outline_color,
                width=2,
                tags="hotspot",
            )

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
