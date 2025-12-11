import random
from typing import List, Optional
from graph import CityGraph
from models.node import Node
from models.vehicle import Vehicle, Motor
from models.request import Request
from search_algorithms import find_route, _heuristic_distance

import osmnx as ox
import math
import pickle
import os

# €
BASE_FARE = 2.50
PRICE_PER_KM = 0.60
CACHE_FILE = "braga_map_cache.pkl"


def generate_map() -> CityGraph:
    place = "Braga, Portugal"

    if os.path.exists(CACHE_FILE):
        print(f"A carregar mapa da cache: {CACHE_FILE}...")
        try:
            with open(CACHE_FILE, "rb") as f:
                city_map = pickle.load(f)

            gas_ev_station_grant_existance(city_map)
            print(f"Mapa carregado: {len(city_map.nos)} nós.")
            return city_map
        except Exception as e:
            print(f"Erro cache: {e}. A gerar novo.")

    print(f"A descarregar grafo OSM para: {place}...")
    G = ox.graph_from_place(place, network_type="drive", simplify=True)

    city_map = CityGraph()
    osmn_to_node = {}

    # Create nodes
    for node_id, data in G.nodes(data=True):
        lon = data.get("x")
        lat = data.get("y")
        if lon is None or lat is None:
            continue
        no = Node((lon, lat), 0, 0, 0)
        osmn_to_node[node_id] = no
        city_map.add_node(no)

    for u, v, key, data in G.edges(keys=True, data=True):
        if u not in osmn_to_node or v not in osmn_to_node:
            continue
        no_u = osmn_to_node[u]
        no_v = osmn_to_node[v]

        length_m = data.get("length", 0)
        length_km = length_m / 1000.0

        # Parse maxspeed if available
        maxspeed = data.get("maxspeed")
        speed_kmh = _parse_maxspeed(maxspeed)

        # No max speed defined
        if speed_kmh is None:
            highway = data.get("highway")
            if highway in ["motorway", "trunk"]:
                speed_kmh = 90.0
            elif highway == "primary":
                speed_kmh = 50.0
            else:
                speed_kmh = 30.0

        if length_km == 0:
            time_minutes = 0
        else:
            time_minutes = (length_km / speed_kmh) * 60.0

        # Speed_kmh to graph
        city_map.add_connection(no_u, no_v, length_km, time_minutes, speed_kmh, True)

    # Get real stations
    _enrich_nodes_with_stations(G, city_map, place)

    # Safety
    all_nodes = list(city_map.nos)
    gas_ev_station_grant_existance(city_map)

    city_map.gas_stations = [n for n in city_map.nos if n.gas_pumps > 0]
    city_map.ev_stations = [n for n in city_map.nos if n.energy_chargers > 0]

    print(
        f"Mapa gerado: {len(all_nodes)} nós (Gas: {len(city_map.gas_stations)}, EV: {len(city_map.ev_stations)})."
    )

    print(f"Mapa gerado com sucesso.")
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(city_map, f)
    except Exception as e:
        print(f"Erro ao guardar cache: {e}")

    return city_map


def _enrich_nodes_with_stations(G, city_map: CityGraph, place: str):
    """
    Tries to find real gas/ev stations
    """
    print("A procurar estações reais (Combustível e EV)...")
    try:
        tags = {"amenity": ["fuel", "charging_station"]}
        gdf = ox.features_from_place(place, tags)  # type: ignore

        if gdf.empty:
            print("Nenhuma estação encontrada no OSM data.")
            return

        count_gas = 0
        count_ev = 0

        for _, row in gdf.iterrows():
            amenity = row.get("amenity")

            if hasattr(row.geometry, "centroid"):
                lon = row.geometry.centroid.x
                lat = row.geometry.centroid.y
            else:
                lon = row.geometry.x
                lat = row.geometry.y

            # Finds nearest node
            nearest_osmn_id = ox.distance.nearest_nodes(G, lon, lat)

            nearest_node_data = G.nodes[nearest_osmn_id]
            n_lon = nearest_node_data["x"]
            n_lat = nearest_node_data["y"]

            target_node = city_map.get_node_by_position((n_lon, n_lat))

            if target_node:
                if amenity == "fuel":
                    target_node.gas_pumps = random.randint(4, 8)
                    count_gas += 1
                elif amenity == "charging_station":
                    target_node.energy_chargers = random.randint(2, 6)
                    target_node.energy_recharge_rate_kw = random.choice(
                        [50, 150, 250]
                    )  # Fast charging
                    count_ev += 1

        print(
            f"Integração Real: {count_gas} Postos Gasolina, {count_ev} Carregadores EV encontrados."
        )

    except Exception as e:
        print(f"Aviso: Não foi possível extrair estações reais ({e}). Usando aleatórias.")


def _parse_maxspeed(ms):
    if ms is None:
        return None
    try:
        if isinstance(ms, list):
            ms = ms[0]
        if isinstance(ms, (int, float)):
            return float(ms)
        if isinstance(ms, str):
            clean = ms.replace(" mph", "").replace(" km/h", "").split(";")[0].strip()
            return float(clean)
    except:
        return None
    return None


def _create_custom_vehicle(
    id_str: str,
    motor: Motor,
    loc: Node,
    pax_capacity: int,
    max_range: float,
    base_cost: float,
    rng: random.Random,
) -> Vehicle:

    # Ajuste de custo por capacidade: Carros maiores gastam mais
    # 7 pax = +15%, 3 pax = -5%
    cost_mult = 1.0
    if pax_capacity == 7:
        cost_mult = 1.15
    elif pax_capacity == 3:
        cost_mult = 0.95

    final_cost = base_cost * cost_mult

    # Começa com  45% e 55% de depósito
    start_range = max_range * rng.uniform(0.45, 0.55)

    return Vehicle(
        id=id_str,
        motor=motor,
        position_node=loc,
        passenger_capacity=pax_capacity,
        price_per_km=final_cost,
        max_km=max_range,
        remaining_km=start_range,
    )


def create_vehicle_fleet(
    all_nodes: List[Node], num_ev: int, num_gas: int, seed: int = 42, use_dynamic_fleet: bool = False
) -> List[Vehicle]:
    """
    Cria a frota de veículos de forma determinística.
    
    Parâmetros:
    - use_dynamic_fleet: Se False (padrão), usa a frota fixa de 10 veículos (5 EV + 5 Gas).
                         Se True, cria dinamicamente num_ev veículos elétricos e num_gas a combustão.
    
    Frota Fixa (padrão):
    - 5 EVs + 5 Gas = 10 veículos
    - Capacidades: 4x(7pax), 4x(4pax), 2x(3pax)
    - Ranges EV: 250-420 km | Gas: 600-900 km
    """
    veiculos = []
    rng = random.Random(seed)

    base_cost_ev = 0.04   # €/km
    base_cost_gas = 0.12  # €/km

    if not use_dynamic_fleet:
        # Configuração Fixa da Frota (Total 10 veículos)
        fleet_specs = [
            # --- ELÉTRICOS---
            (Motor.ELECTRIC, 3, 250, "EV-Smart"),
            (Motor.ELECTRIC, 4, 300, "EV-Sedan1"),
            (Motor.ELECTRIC, 4, 350, "EV-Sedan2"),
            (Motor.ELECTRIC, 7, 380, "EV-Van1"),
            (Motor.ELECTRIC, 7, 420, "EV-Van2"),
            # --- COMBUSTÃO ---
            (Motor.COMBUSTION, 3, 600, "Gas-Compact"),
            (Motor.COMBUSTION, 4, 700, "Gas-Sedan1"),
            (Motor.COMBUSTION, 4, 750, "Gas-Sedan2"),
            (Motor.COMBUSTION, 7, 800, "Gas-Van1"),
            (Motor.COMBUSTION, 7, 900, "Gas-Van2"),
        ]

        for motor, pax, max_range, name in fleet_specs:
            loc = rng.choice(all_nodes)
            cost = base_cost_ev if motor == Motor.ELECTRIC else base_cost_gas
            v = _create_custom_vehicle(name, motor, loc, pax, float(max_range), cost, rng)
            veiculos.append(v)

        print(f"Frota fixa gerada ({len(veiculos)} veículos). Seed: {seed}")
    else:
        ev_specs = [
            (3, 250, "EV-Smart"),
            (4, 300, "EV-Sedan"),
            (4, 350, "EV-Sedan"),
            (7, 380, "EV-Van"),
            (7, 420, "EV-Van"),
        ]
        gas_specs = [
            (3, 600, "Gas-Compact"),
            (4, 700, "Gas-Sedan"),
            (4, 750, "Gas-Sedan"),
            (7, 800, "Gas-Van"),
            (7, 900, "Gas-Van"),
        ]

        for i in range(num_ev):
            spec = ev_specs[i % len(ev_specs)]
            pax, max_range, base_name = spec
            name = f"{base_name}-{i+1}"
            loc = rng.choice(all_nodes)
            v = _create_custom_vehicle(name, Motor.ELECTRIC, loc, pax, float(max_range), base_cost_ev, rng)
            veiculos.append(v)

        for i in range(num_gas):
            spec = gas_specs[i % len(gas_specs)]
            pax, max_range, base_name = spec
            name = f"{base_name}-{i+1}"
            loc = rng.choice(all_nodes)
            v = _create_custom_vehicle(name, Motor.COMBUSTION, loc, pax, float(max_range), base_cost_gas, rng)
            veiculos.append(v)

        print(f"Frota dinâmica gerada ({num_ev} EV + {num_gas} Gas = {len(veiculos)} veículos). Seed: {seed}")

    return veiculos


def gas_ev_station_grant_existance(city_map: CityGraph):
    all_nodes = list(city_map.nos)
    if not any(n.energy_chargers > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.energy_chargers = random.randint(2, 4)
        no_a_converter.energy_recharge_rate_kw = 50
        city_map.ev_stations.append(no_a_converter)

    if not any(n.gas_pumps > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.gas_pumps = random.randint(2, 4)
        city_map.gas_stations.append(no_a_converter)
