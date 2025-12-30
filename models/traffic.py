from noise import pnoise3, pnoise1
from typing import Tuple, Dict
import math


class TrafficManager:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.noise_scale = 3.5

        self.time_scale = 0.02

        self.center_coords = (-8.42, 41.55)

        self.weather_time_scale = 0.002
        self.current_weather_condition = "Sol"
        self.current_weather_penalty = 1.0

        # Cache: {(lat_idx, lon_idx): traffic_factor}
        self._cache: Dict[Tuple[int, int], float] = {}
        self._last_time_block: float = -1.0
        # Noise precision
        self.grid_precision = 0.002

    def get_traffic_factor(self, position: Tuple[float, float], time_minutes: float) -> float:
        # Traffic clock
        current_time_block = time_minutes - (time_minutes % 10)

        if current_time_block != self._last_time_block:
            self._cache.clear()
            self._update_weather(time_minutes)
            self._last_time_block = current_time_block

        lon, lat = position
        lon_idx = int(lon / self.grid_precision)
        lat_idx = int(lat / self.grid_precision)
        cache_key = (lon_idx, lat_idx)

        # Get from cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Miss
        grid_lon = lon_idx * self.grid_precision
        grid_lat = lat_idx * self.grid_precision

        factor = self._calculate_heavy_math(grid_lon, grid_lat, current_time_block)

        # Cache save (com weather penalty)
        cached_value = factor * self.current_weather_penalty
        self._cache[cache_key] = cached_value

        return cached_value

    def _calculate_heavy_math(self, lon: float, lat: float, time_minutes: float) -> float:
        rush_intensity = self._get_rush_intensity((time_minutes / 60.0) % 24)

        # Noise
        x_noise = (lon - self.center_coords[0]) * 100 * self.noise_scale
        y_noise = (lat - self.center_coords[1]) * 100 * self.noise_scale
        z_time = time_minutes * self.time_scale

        noise_val = pnoise3(x_noise, y_noise, z_time, octaves=2, persistence=0.5)
        noise_val = (noise_val + 1) / 2.0

        # Centro da cidade
        dist = math.sqrt((lon - self.center_coords[0]) ** 2 + (lat - self.center_coords[1]) ** 2)
        center_influence = max(0.0, 1.0 - (dist / 0.04))
        raw_congestion = noise_val + (center_influence * 0.45)

        # Threshold
        traffic_threshold = 0.55

        if raw_congestion < traffic_threshold:
            return 1.0

        excess_traffic = raw_congestion - traffic_threshold

        penalty = excess_traffic * (rush_intensity * 5.0)

        return 1.0 + penalty

    def _get_rush_intensity(self, hour: float) -> float:
        """
        Retorna a intensidade usando soma de curvas Gaussianas para suavidade total.
        Evita os 'saltos' bruscos que faziam o trânsito contrair de repente.
        """
        base_intensity = 0.1

        def gaussian(h, peak, intensity, width):
            return intensity * math.exp(-((h - peak) ** 2) / (2 * width**2))

        # Manhã: Pico 08:30
        morning = gaussian(hour, 8.5, 0.6, 1.5)
        # Almoço: Pico 13:00
        lunch = gaussian(hour, 13.0, 0.2, 1.2)
        # Tarde: Pico 18:00 (O maior)
        evening = gaussian(hour, 18.0, 0.8, 1.8)
        # Noite: Pico 21:00
        night = gaussian(hour, 21.0, 0.1, 1.5)

        total = base_intensity + morning + lunch + evening + night
        return min(1.0, total)

    def _update_weather(self, time_minutes: float):
        # pnoise1 retorna valor entre -1 e 1 (aprox)
        noise = pnoise1(time_minutes * self.weather_time_scale, base=self.seed + 1000)

        # Normalizar para [0, 1]
        val = (noise + 1) / 2.0

        if val < 0.45:
            self.current_weather_condition = "Sol"
            self.current_weather_penalty = 1.0
        elif val < 0.65:
            self.current_weather_condition = "Nublado"
            self.current_weather_penalty = 1.0
        elif val < 0.85:
            self.current_weather_condition = "Chuva"
            self.current_weather_penalty = 1.30
        else:
            self.current_weather_condition = "Tempestade"
            self.current_weather_penalty = 1.60
