import random
from typing import List, Optional
from graph import CityGraph
from models.node import Node
from models.vehicle import Vehicle, Motor
from models.request import Request
from search import find_a_star_route, _heuristic_distance

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


def generate_random_request(
    map: CityGraph, nos: List[Node], creation_time: float, force_start_node: Optional[Node] = None
) -> Request:
    if force_start_node:
        start_node = force_start_node
    else:
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

    # Nearest stations from the end_node using heurística for efficiency
    nearest_ev_path = None
    nearest_ev_dist = float("inf")

    if map.ev_stations:
        closest_ev_node = min(map.ev_stations, key=lambda s: _heuristic_distance(end_node, s))

        # Calculate only A* for the closest station
        path_info = find_a_star_route(map, end_node, closest_ev_node)
        if path_info:
            nearest_ev_path, _, nearest_ev_dist = path_info
        else:
            nearest_ev_dist = _heuristic_distance(end_node, closest_ev_node)

    nearest_gas_path = None
    nearest_gas_dist = float("inf")

    if map.gas_stations:
        closest_gas_node = min(map.gas_stations, key=lambda s: _heuristic_distance(end_node, s))

        # Calculate only A* for the closest station
        path_info = find_a_star_route(map, end_node, closest_gas_node)
        if path_info:
            nearest_gas_path, _, nearest_gas_dist = path_info
        else:
            nearest_gas_dist = _heuristic_distance(end_node, closest_gas_node)

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
        nearest_ev_station_path=nearest_ev_path,
        nearest_ev_station_distance=nearest_ev_dist,
        nearest_gas_station_path=nearest_gas_path,
        nearest_gas_station_distance=nearest_gas_dist,
    )
