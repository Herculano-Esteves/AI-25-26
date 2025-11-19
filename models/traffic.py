from noise import pnoise3
from typing import Tuple
import math


class TrafficManager:
    def __init__(self, seed: int = 42):
        self.seed = seed
        # Ajuste para 'zoom' do ruído no mapa.
        # 0.15 cria zonas de trânsito médias (bairros inteiros).
        self.noise_scale = 0.15

        # Ajuste para a velocidade da mudança no tempo.
        # 0.05 significa que o padrão muda lentamente minuto a minuto.
        self.time_scale = 0.05

        # Coordenadas aproximadas do centro de Braga (para penalizar o centro)
        self.center_coords = (-8.42, 41.55)

    def get_traffic_factor(self, position: Tuple[float, float], time_minutes: float) -> float:
        """
        Retorna um multiplicador de tempo (>= 1.0).
        Ex: 1.0 = Sem trânsito. 2.0 = Tempo de viagem duplicado.
        """
        lon, lat = position

        # 1. Fator Hora de Ponta (Determinístico - "A onda diária")
        hour_of_day = (time_minutes / 60.0) % 24
        rush_factor = self._get_rush_hour_multiplier(hour_of_day)

        # Se for de madrugada (fator < 1.1), ignoramos o ruído espacial para poupar recursos
        if rush_factor <= 1.05:
            return 1.0

        # 2. Fator Ruído Perlin (Variação Local e Temporal)
        # pnoise3(x, y, z) -> Gera um valor suave entre -1 e 1
        # Usamos o 'time_minutes' no eixo Z para evoluir o padrão no tempo.
        noise_val = pnoise3(
            (lon * 100) * self.noise_scale,
            (lat * 100) * self.noise_scale,
            time_minutes * self.time_scale,
            octaves=2,
            persistence=0.5,
        )

        # Normalizar de [-1, 1] para [0, 1]
        noise_val = (noise_val + 1) / 2.0

        # 3. Penalização do Centro Urbano
        dist = math.sqrt((lon - self.center_coords[0]) ** 2 + (lat - self.center_coords[1]) ** 2)
        # Zonas a menos de ~4km do centro sofrem mais efeito do trânsito
        center_bias = max(0.0, 1.0 - (dist / 0.04))

        # O 'noise_val' define ONDE está o trânsito agora.
        # O 'rush_factor' define a INTENSIDADE máxima possível nesta hora.
        # O 'center_bias' agrava a situação no centro.

        congestion_level = noise_val * (0.5 + (center_bias * 0.5))

        # Fórmula: Base (1.0) + (Intensidade da Hora * Congestionamento Local)
        # Se for hora de ponta (2.0) e estivermos num pico de ruído (1.0), o fator será alto.
        final_factor = 1.0 + ((rush_factor - 1.0) * congestion_level * 2.0)

        return max(1.0, final_factor)

    def _get_rush_hour_multiplier(self, hour: float) -> float:
        """Define a intensidade global do trânsito consoante a hora."""
        # Manhã (07h - 10h)
        if 7 <= hour < 10:
            return 1.6
        # Almoço (12h - 14h)
        elif 12 <= hour < 14:
            return 1.3
        # Tarde (17h - 20h)
        elif 17 <= hour < 20:
            return 1.8
        # Madrugada
        elif hour < 6 or hour > 23:
            return 1.0

        return 1.1
