from noise import pnoise3
from typing import Tuple, Dict
import math


class TrafficManager:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.noise_scale = 3.5
        self.time_scale = 0.05
        self.center_coords = (-8.42, 41.55)

        # Cache: {(lat_idx, lon_idx): traffic_factor}
        self._cache: Dict[Tuple[int, int], float] = {}
        self._last_time_block: float = -1.0
        # Noise precision
        self.grid_precision = 0.002

    def get_traffic_factor(self, position: Tuple[float, float], time_minutes: float) -> float:
        # Traffic clock
        current_time_block = time_minutes - (time_minutes % 15)
        
        if current_time_block != self._last_time_block:
            self._cache.clear()
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
        
        # Cache save
        self._cache[cache_key] = factor
        
        return factor

    def _calculate_heavy_math(self, lon: float, lat: float, time_minutes: float) -> float:
        """
        Contém a tua lógica original de noise, distâncias e threshold.
        Só é chamada se o valor não existir na cache.
        """

        rush_intensity = self._get_rush_intensity((time_minutes / 60.0) % 24)

        # Noise
        x_noise = (lon - self.center_coords[0]) * 100 * self.noise_scale
        y_noise = (lat - self.center_coords[1]) * 100 * self.noise_scale
        z_time = time_minutes * self.time_scale

        noise_val = pnoise3(x_noise, y_noise, z_time, octaves=2, persistence=0.5)
        noise_val = (noise_val + 1) / 2.0

        # Center of city filter to make the trafic be on the middle of Braga
        dist = math.sqrt((lon - self.center_coords[0]) ** 2 + (lat - self.center_coords[1]) ** 2)
        center_influence = max(0.0, 1.0 - (dist / 0.04))
        raw_congestion = noise_val + (center_influence * 0.45)

        # Will remove traffic the furthest it is from the center
        traffic_threshold = 0.55 

        if raw_congestion < traffic_threshold:
            return 1.0

        excess_traffic = raw_congestion - traffic_threshold

        gain = rush_intensity * 5.0
        
        penalty = excess_traffic * gain
        
        return 1.0 + penalty

    def _get_rush_intensity(self, hour: float) -> float:
        """
        Retorna a intensidade do caos entre 0.0 (calmo) e 1.0 (caos total).
        """
        # Manhã (07h30 - 09h30)
        if 7.5 <= hour < 9.5:
            return 0.7 
        
        # Almoço (12h - 14h)
        elif 12 <= hour < 14:
            return 0.3
            
        # Tarde (17h - 19h30) - Pico Máximo
        elif 17 <= hour < 19.5:
            return 0.9
            
        # Pré-noite (19h30 - 21h)
        elif 19.5 <= hour < 21:
            return 0.2
            
        # Madrugada / Noite
        elif hour < 6.5 or hour > 22:
            return 0.1
            
        # Base do dia
        return 0.1