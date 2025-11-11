import random
from typing import List

from graph import CityGraph
from models.node import Node
from models.vehicle import Vehicle, Motor
from models.request import Request
from search import find_a_star_route

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

    # Cache
    if os.path.exists(CACHE_FILE):
        print(f"A carregar mapa da cache: {CACHE_FILE}...")
        try:
            with open(CACHE_FILE, "rb") as f:
                city_map = pickle.load(f)
            
            gas_ev_station_grant_existance(list(city_map.nos))
            
            print(f"Mapa OSM carregado da cache: {len(city_map.nos)} nós.")
            return city_map
        except Exception as e:
            print(f"Erro ao carregar cache {CACHE_FILE}: {e}. A gerar novo mapa.")

    print(f"Carregando rede OSM para: {place} (pode demorar alguns segundos)...")
    G = ox.graph_from_place(place, network_type="drive")

    city_map = CityGraph()

    osmn_to_node = {}

    # Create nodes
    for node_id, data in G.nodes(data=True):
        lon = data.get("x")
        lat = data.get("y")
        if lon is None or lat is None:
            continue
        pos = (lon, lat)
        no = Node(pos, 0, 0, random.randint(200, 900))
        osmn_to_node[node_id] = no
        city_map.add_node(no)

    # helper to parse maxspeed if available
    def _parse_maxspeed(ms):
        if ms is None:
            return None
        try:
            if isinstance(ms, (int, float)):
                return float(ms)
            if isinstance(ms, str):
                # Take first number
                for part in ms.split(";"):
                    part = part.strip()
                    try:
                        return float(part)
                    except Exception:
                        continue
        except Exception:
            return None
        return None

    # Create connections from edges
    for u, v, key, data in G.edges(keys=True, data=True):
        if u not in osmn_to_node or v not in osmn_to_node:
            continue
        no_u = osmn_to_node[u]
        no_v = osmn_to_node[v]

        length_m = data.get("length")
        if length_m is None:
            lon1, lat1 = no_u.position
            lon2, lat2 = no_v.position
            R = 6371.0
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            sa = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
            c = 2 * math.atan2(math.sqrt(sa), math.sqrt(1 - sa))
            length_km = (R * c)
        else:
            length_km = length_m / 1000.0

        # estimate travel speed
        speed = None
        maxspeed = data.get("maxspeed")
        speed = _parse_maxspeed(maxspeed)
        if speed is None:
            speed = data.get("speed_kph") or data.get("speed")
        if speed is None:
            speed = 30.0

        # time in minutes
        time_minutes = (length_km / float(speed)) * 60.0 if speed > 0 else (length_km / 30.0) * 60.0

        # add connection (bidirectional)
        city_map.add_connection(no_u, no_v, length_km, time_minutes, True)

    all_nodes = list(city_map.nos)
    gas_ev_station_grant_existance(all_nodes)

    print(f"Mapa OSM carregado: {len(all_nodes)} nós, {len(G.edges())} arestas (approx).")

    # Save in cache
    try:
        print(f"A guardar mapa na cache: {CACHE_FILE}...")
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(city_map, f)
        print("Mapa guardado com sucesso.")
    except Exception as e:
        print(f"Erro ao guardar mapa na cache: {e}")

    return city_map


def _create_vehicle(
    id_prefix: str,
    motor: Motor,
    loc: Node,
    cost_per_km: float,
    range: int,
    max_range: int,
) -> Vehicle:
    return Vehicle(
        f"V-{id_prefix}",
        motor,
        loc,
        random.randint(3, 7),
        cost_per_km,
        random.randint(range, max_range),
        random.randint(50, range),
    )


def create_vehicle_fleet(all_nodes: List[Node], num_ev: int, num_gas: int) -> List[Vehicle]:
    veiculos = []

    # Generates eletric vehicles
    for i in range(num_ev):
        loc = random.choice(all_nodes)
        veiculos.append(_create_vehicle(f"EV{i+1}", Motor.ELECTRIC, loc, 0.035, 50, 650))

    # Generates combustion vehicles
    for i in range(num_gas):
        loc = random.choice(all_nodes)
        veiculos.append(_create_vehicle(f"GAS{i+1}", Motor.COMBUSTION, loc, 0.098, 50, 900))

    print(f"Frota gerada: {len(veiculos)} veículos criados.")
    return veiculos


def generate_requests(
    map: CityGraph, all_nodes: List[Node], num_requests: int, creation_time: float
) -> List[Request]:

    requests = []
    for _ in range(num_requests):
        requests.append(generate_random_request(map, all_nodes, creation_time))
    print(f"Pedidos gerados: {len(requests)} requests iniciais criados.")
    return requests


def gas_ev_station_grant_existance(all_nodes):
    if not any(n.energy_chargers > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.energy_chargers = random.randint(2, 4)

    if not any(n.gas_pumps > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.gas_pumps = random.randint(2, 4)


def generate_random_request(map: CityGraph, nos: List[Node], creation_time: float) -> Request:
    start_node = random.choice(nos)
    end_node = random.choice(nos)
    while start_node == end_node:
        end_node = random.choice(nos)

    price = 0.0
    path, time, distance = None, 0.0, 0.0

    result = find_a_star_route(map, start_node, end_node)
    if result:
        path, time, distance = result
        price = BASE_FARE + (distance * PRICE_PER_KM)

    req_priority = random.randint(1, 5)

    return Request(
        start_node=start_node,
        end_node=end_node,
        passenger_capacity=random.randint(1, 7),
        creation_time=creation_time,
        price=price,
        priority=req_priority,
        environmental_preference=True if random.randint(1, 4) == 1 else False,
        path=path,
        path_distance=distance,
        path_time=time,
    )