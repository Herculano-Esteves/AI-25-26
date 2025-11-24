import time
import json
import concurrent.futures
import traceback
from typing import List, Dict, Any, Callable
from Simulation.simulator import Simulator
from Simulation.request_simulation import set_selected_algorithm, set_selected_assignment_algorithm


def run_benchmark_task(config, ticks_to_run, duration_hours):
    """
    Esta função roda em um PROCESSO SEPARADO.
    Ela deve instanciar seu próprio simulador ou receber um estado inicial limpo.
    """
    routing, assignment = config

    try:
        local_simulator = Simulator()

        print(f"[Processo] Iniciando: {routing} / {assignment}")

        # Setup Global
        set_selected_algorithm(routing)
        set_selected_assignment_algorithm(assignment)

        local_simulator.reset_simulation_state()

        start_real_time = time.time()

        # Loop de simulação
        for _ in range(ticks_to_run):
            local_simulator.simulation_step(time_multiplier=1.0)

        end_real_time = time.time()
        duration_sec = end_real_time - start_real_time

        stats = local_simulator.stats

        # Algorithm Types
        routing_type = "Informado" if routing in ["astar", "greedy"] else "Não Informado"
        assign_type = (
            "Otimização" if assignment in ["simulated annealing", "hill climbing"] else "Heurística"
        )

        def safe_div(n, d):
            return n / d if d > 0 else 0.0

        result = {
            "routing": routing,
            "assignment": assignment,
            "routing_type": routing_type,
            "assignment_type": assign_type,
            "duration_sim_hours": duration_hours,
            "duration_real_sec": round(duration_sec, 2),
            "total_revenue": stats.total_revenue_generated,
            "total_cost": stats.total_operational_cost,
            "profit": stats.total_revenue_generated - stats.total_operational_cost,
            "total_requests_completed": stats.total_requests_completed,
            "total_requests_failed": stats.total_requests_failed,
            "total_kms": stats.total_kms_driven,
            "total_kms_empty": stats.total_kms_driven_empty,
            "total_kms_occupied": stats.total_kms_driven_with_passenger,
            "avg_wait_time": safe_div(
                stats.total_wait_time_for_pickup, stats.total_requests_picked_up
            ),
            "max_wait_time": stats.max_wait_time if stats.max_wait_time != float("-inf") else 0,
            "avg_trip_time": safe_div(
                stats.total_time_for_completed_requests, stats.total_requests_completed
            ),
            "total_co2": stats.total_co2_emitted,
            "vehicles_unavailable_count": stats.step_vehicles_unavailable,
            "occupancy_rate": safe_div(
                stats.total_kms_driven_with_passenger, stats.total_kms_driven
            ),
            "ev_kms_ratio": safe_div(stats.total_kms_driven_ev, stats.total_kms_driven),
            "ev_occupancy_rate": safe_div(
                stats.total_kms_driven_ev - stats.total_kms_driven_empty_ev,
                stats.total_kms_driven_ev,
            ),
            "gas_occupancy_rate": safe_div(
                stats.total_kms_driven_gas - stats.total_kms_driven_empty_gas,
                stats.total_kms_driven_gas,
            ),
            "ev_station_time": stats.total_station_time_ev,
            "gas_station_time": stats.total_station_time_gas,
        }

        return result

    except Exception as e:
        print(f"Erro no processo {routing}/{assignment}: {e}")
        traceback.print_exc()
        return None


class BenchmarkRunner:
    def __init__(
        self, update_callback: Callable[[str], None], completion_callback: Callable[[], None]
    ):
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.is_running = False
        self.should_stop = False
        self.results = []
        self.executor = None

        self.configs = [
            ("astar", "simulated annealing"),
            ("astar", "greedy"),
            ("astar", "hill climbing"),
            ("bfs", "simulated annealing"),
            ("bfs", "greedy"),
            ("bfs", "hill climbing"),
            ("greedy", "simulated annealing"),
            ("greedy", "greedy"),
            ("greedy", "hill climbing"),
        ]

        self.simulation_duration_hours = 24 * 7 * 2
        self.ticks_to_run = int((self.simulation_duration_hours * 60) / Simulator.SIM_TIME_PER_TICK)

    def start_benchmark(self):
        if self.is_running:
            return

        self.is_running = True
        self.should_stop = False
        self.results = []

        import threading

        threading.Thread(target=self._run_parallel_manager, daemon=True).start()

    def stop_benchmark(self):
        self.should_stop = True
        if self.executor:
            print("[Benchmark] Forçando encerramento dos processos...")
            self.executor.shutdown(wait=False, cancel_futures=True)

    def _run_parallel_manager(self):
        print("[Benchmark] Iniciando suite em PARALELO...")

        # max_workers=None usa o número de CPUs disponíveis
        with concurrent.futures.ProcessPoolExecutor() as executor:
            self.executor = executor
            future_to_config = {}

            # Submete todas as tarefas
            for config in self.configs:
                if self.should_stop:
                    break

                # Tarefa para o pool
                future = executor.submit(
                    run_benchmark_task, config, self.ticks_to_run, self.simulation_duration_hours
                )
                future_to_config[future] = config

            # Processa os resultados conforme ficam prontos
            for future in concurrent.futures.as_completed(future_to_config):
                if self.should_stop:
                    break

                config = future_to_config[future]
                try:
                    data = future.result()

                    if data:
                        self.results.append(data)
                        self._save_single_result(data)

                        # Callback para a UI (thread-safe geralmente necessário dependendo do framework GUI)
                        msg = f"Finalizado: {data['routing']}/{data['assignment']} (Lucro: {data['profit']:.2f})"
                        self.update_callback(msg)
                    else:
                        self.update_callback(f"Falha em: {config}")

                except Exception as exc:
                    print(f"Gerou exceção: {exc}")

        self.is_running = False
        self.completion_callback()
        print("[Benchmark] Todos os processos finalizados.")

    def _save_single_result(self, result: Dict[str, Any]):
        import os

        directory = "benchmark_results"
        if not os.path.exists(directory):
            os.makedirs(directory)

        filename = f"{directory}/{result['routing']}_{result['assignment'].replace(' ', '_')}.json"
        try:
            with open(filename, "w") as f:
                json.dump(result, f, indent=4)
        except Exception as e:
            print(f"[Benchmark] Erro ao salvar: {e}")
