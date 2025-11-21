class PlanningConfig:
    """
    All the weights
    """

    # Pesos Base
    WEIGHT_TIME = 1.0  # Peso de 1 minuto de viagem
    WEIGHT_PRIORITY = 30.0  # Quanto vale cada nível de prioridade
    WEIGHT_AGE = 4.0  # Peso por minuto de espera

    # Penalizações "Hard"
    PENALTY_IMPOSSIBLE = float("inf")

    # Penalização dinâmica por Km
    PENALTY_ENV_MISMATCH_PER_KM = 15.0

    PENALTY_UNUSED_SEAT = 5.0  # Por lugar vazio

    # Penalizações
    BATTERY_RISK_EXPONENT = 2.0  # Quão agressiva é a curva de risco (quadrática/exponencial)
    BATTERY_CRITICAL_LEVEL = 30.0  # Abaixo disto, o risco dispara
    WEIGHT_BATTERY_RISK = 20.0  # Multiplicador do fator de risco

    WEIGHT_ISOLATION = 1  # Custo por km de distância de um Hotspot após entrega
    WEIGHT_FUTURE_REFUEL = 1.5  # Custo por km até à estação mais próxima APÓS entrega

    # Custo de Oportunidade
    WEIGHT_LOST_OPPORTUNITY = 40.0  # EV a fazer pedido não-ecológico quando há ecológicos na fila

    BACKLOG_BASE_PENALTY = 160.0  # Custo fixo por deixar alguém para trás

    # Profit Optimization
    WEIGHT_PROFIT = 10.0  # Multiplier for profit (negative cost)
