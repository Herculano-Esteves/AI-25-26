import time
import json

from typing import List, Dict, Any, Callable
from Simulation.simulator import Simulator
from Simulation.request_simulation import set_selected_algorithm, set_selected_assignment_algorithm

class BenchmarkRunner:
    def __init__(self, simulator: Simulator, update_callback: Callable[[str], None], completion_callback: Callable[[], None]):
        self.simulator = simulator
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.is_running = False
        self.should_stop = False
        self.results = []
        
        self.configs = [
            ('astar', 'simulated annealing'),
            ('astar', 'greedy'),
            ('astar', 'hill climbing'),
            ('bfs', 'simulated annealing'),
            ('bfs', 'greedy'),
            ('bfs', 'hill climbing'),
            ('greedy', 'simulated annealing'),
            ('greedy', 'greedy'),
            ('greedy', 'hill climbing'),
        ]
        
        self.current_config_index = 0
        self.simulation_duration_hours = 24  # 1 Days
        self.ticks_to_run = self.simulation_duration_hours * 60  # 1 tick = 1 min
        
    def start_benchmark(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.should_stop = False
        self.results = []
        self.current_config_index = 0
        
        self._run_loop()
        
    def stop_benchmark(self):
        self.should_stop = True
        
    def _run_loop(self):
        print("[Benchmark] Starting benchmark suite...")
        try:
            for routing, assignment in self.configs:
                if self.should_stop:
                    print("[Benchmark] Stop requested.")
                    break
                    
                self.update_callback(f"Running: Routing={routing}, Assign={assignment}")
                print(f"[Benchmark] Setup: {routing} / {assignment}")
                
                # Setup
                try:
                    set_selected_algorithm(routing)
                    set_selected_assignment_algorithm(assignment)
                    
                    # Reset Simulation
                    print("[Benchmark] Resetting simulation state...")
                    self.simulator.reset_simulation_state()
                    
                    # Run Simulation
                    start_real_time = time.time()
                    print(f"[Benchmark] Running simulation for {self.ticks_to_run} ticks...")
                    
                    # Fast forward loop
                    for i in range(self.ticks_to_run):
                        if self.should_stop:
                            break
                        self.simulator.simulation_step(time_multiplier=1.0)
                        if i % 100 == 0:
                            pass
                        
                    end_real_time = time.time()
                    duration_sec = end_real_time - start_real_time
                    
                    # Collect Stats
                    stats = self.simulator.stats
                    
                    # Determine Algorithm Types
                    routing_type = "Informado" if routing in ['astar', 'greedy'] else "Não Informado"
                    assign_type = "Otimização" if assignment in ['simulated annealing', 'hill climbing'] else "Heurística"

                    # Helper for safe division
                    def safe_div(n, d):
                        return n / d if d > 0 else 0.0

                    result = {
                        "routing": routing,
                        "assignment": assignment,
                        "routing_type": routing_type,
                        "assignment_type": assign_type,
                        "duration_sim_hours": self.simulation_duration_hours,
                        "duration_real_sec": round(duration_sec, 2),
                        "total_revenue": stats.total_revenue_generated,
                        "total_cost": stats.total_operational_cost,
                        "profit": stats.total_revenue_generated - stats.total_operational_cost,
                        "total_requests_completed": stats.total_requests_completed,
                        "total_requests_failed": stats.total_requests_failed,
                        "total_kms": stats.total_kms_driven,
                        "total_kms_empty": stats.total_kms_driven_empty,
                        "total_kms_occupied": stats.total_kms_driven_with_passenger,
                        "avg_wait_time": safe_div(stats.total_wait_time_for_pickup, stats.total_requests_picked_up),
                        "max_wait_time": stats.max_wait_time if stats.max_wait_time != float('-inf') else 0,
                        "avg_trip_time": safe_div(stats.total_time_for_completed_requests, stats.total_requests_completed),
                        "total_co2": stats.total_co2_emitted,
                        "vehicles_unavailable_count": stats.step_vehicles_unavailable,
                        "occupancy_rate": safe_div(stats.total_kms_driven_with_passenger, stats.total_kms_driven),
                        "ev_kms_ratio": safe_div(stats.total_kms_driven_ev, stats.total_kms_driven),
                        "ev_occupancy_rate": safe_div(stats.total_kms_driven_ev - stats.total_kms_driven_empty_ev, stats.total_kms_driven_ev),
                        "gas_occupancy_rate": safe_div(stats.total_kms_driven_gas - stats.total_kms_driven_empty_gas, stats.total_kms_driven_gas),
                        "ev_station_time": stats.total_station_time_ev,
                        "gas_station_time": stats.total_station_time_gas
                    }
                    
                    self.results.append(result)
                    self._save_single_result(result)
                    print(f"[Benchmark] Finished {routing}/{assignment}. Profit: {result['profit']:.2f}")
                except Exception as e:
                    print(f"[Benchmark] Error in run {routing}/{assignment}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
        except Exception as e:
            print(f"[Benchmark] Fatal error in loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("[Benchmark] Loop finished or crashed. Cleaning up.")
            self.is_running = False
            self.completion_callback()
        
    def _save_single_result(self, result: Dict[str, Any]):
        import os
        directory = "benchmark_results"
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        filename = f"{directory}/{result['routing']}_{result['assignment'].replace(' ', '_')}.json"
        try:
            with open(filename, "w") as f:
                json.dump(result, f, indent=4)
            print(f"[Benchmark] Result saved to {filename}")
        except Exception as e:
            print(f"[Benchmark] Error saving result: {e}")
