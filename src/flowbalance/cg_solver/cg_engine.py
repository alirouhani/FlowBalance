import logging
from typing import Dict, Any, List, Set
from ortools.linear_solver import pywraplp
from flowbalance.core.entities import Network

try:
    import _flowbalance_pricing as fbp
    CPP_PRICING_AVAILABLE = True
except ImportError:
    CPP_PRICING_AVAILABLE = False


class ColumnGenerationSolver:
    def __init__(self):
        self.solver = pywraplp.Solver.CreateSolver('GLOP')

    def solve(self, network: Network, horizon: int, max_iterations: int = 200) -> Dict[str, Any]:
        if not CPP_PRICING_AVAILABLE:
            raise ImportError("C++ Pricing Engine module is strictly required.")

        self.solver.Clear()
        
        node_db = {node.id: node for node in network.nodes}
        
        unique_coords = set()
        for node in network.nodes:
            for t in range(horizon + 1):
                unique_coords.add((node.id, t))
                
        node_indexer = {coord: idx for idx, coord in enumerate(sorted(list(unique_coords)))}
        
        cpp_arcs = []
        arc_capacity_map = []
        arc_identities = [] 
        
        arc_counter = 0
        
        # Generate Temporal Inventory Holding Arcs
        for u_id in node_db.keys():
            for t in range(horizon):
                u_coord = node_indexer[(u_id, t)]
                v_coord = node_indexer[(u_id, t + 1)]
                node_obj = node_db[u_id]
                
                capacity = node_obj.capacity_limit if node_obj.capacity_limit != float('inf') else 1e6
                
                cpp_arcs.append(fbp.TimeSpaceArc(arc_counter, u_coord, v_coord, 0.0))
                arc_capacity_map.append(capacity)
                arc_identities.append(("holding", u_id, u_id))
                arc_counter += 1
                
        # Generate Spatial Movement Transport Arcs
        for edge in network.edges:
            for t in range(horizon + 1):
                arrival_time = t + edge.transit_time
                if arrival_time <= horizon:
                    u_coord = node_indexer[(edge.from_node, t)]
                    v_coord = node_indexer[(edge.to_node, arrival_time)]
                    
                    capacity = edge.shared_capacity_limit if edge.shared_capacity_limit != float('inf') else 1e6
                    
                    cpp_arcs.append(fbp.TimeSpaceArc(arc_counter, u_coord, v_coord, 0.0))
                    arc_capacity_map.append(capacity)
                    arc_identities.append(("transit", edge.from_node, edge.to_node))
                    arc_counter += 1

        cpp_commodities = []
        for i, comm in enumerate(network.commodities):
            # Include volume and consumption factor parameters into the C++ bindings
            cpp_commodities.append(fbp.CommodityCore(
                i, 
                node_indexer[(comm.origin, comm.available_time)], 
                node_indexer[(comm.destination, comm.due_date)],
                comm.volume,
                comm.consumption_factor
            ))

        # Master Constraints Setup
        capacity_constraints = [self.solver.Constraint(-self.solver.infinity(), cap, f"cap_{idx}") for idx, cap in enumerate(arc_capacity_map)]
        convexity_constraints = [self.solver.Constraint(1.0, 1.0, f"conv_{i}") for i in range(len(network.commodities))]
        
        objective = self.solver.Objective()
        objective.SetMinimization()

        path_tracking: Dict[int, List[List[int]]] = {i: [] for i in range(len(network.commodities))}
        lambda_vars: List[pywraplp.Variable] = []
        path_var_map: Dict[pywraplp.Variable, List[int]] = {}
        
        for i, comm in enumerate(network.commodities):
            var = self.solver.NumVar(0.0, self.solver.infinity(), f"artificial_{i}")
            objective.SetCoefficient(var, 1e6) 
            convexity_constraints[i].SetCoefficient(var, 1.0)
            lambda_vars.append(var)

        iteration = 0
        last_obj_val = float('inf')
        
        while iteration < max_iterations:
            status = self.solver.Solve()
            if status != pywraplp.Solver.OPTIMAL:
                logging.error("RMP Infeasible.")
                break

            current_obj_val = objective.Value()
            
            dual_w = [c.DualValue() for c in capacity_constraints]
            dual_alpha = [c.DualValue() for c in convexity_constraints]

            # 1. Stall-Detection Fallback Check
            if abs(last_obj_val - current_obj_val) < 1e-4 and iteration > 0:
                filter_active = False 
            else:
                filter_active = True

            last_obj_val = current_obj_val

            # 2. Dual-Variable Heuristic Filtering
            pricing_pool_indices: Set[int] = set()
            if filter_active:
                negative_dual_arcs = {idx for idx, w in enumerate(dual_w) if w < -1e-6}
                # Filter the pool: Only include commodities that are currently utilizing 
                # at least one of these bottleneck arcs in their active paths.
                for var, arc_ids in path_var_map.items():
                    if var.solution_value() > 1e-6:
                        if any(arc in negative_dual_arcs for arc in arc_ids):
                            comm_id = int(var.name().split('_c')[1].split('_')[0])
                            pricing_pool_indices.add(comm_id)
            
            # 3. Dynamic Fallback Allocation
            if not pricing_pool_indices or not filter_active:
                pricing_pool_indices = set(range(len(network.commodities)))

            new_columns_total = []

            for comm_idx in pricing_pool_indices:
                comm = network.commodities[comm_idx]

                for arc_idx, (arc_type, src, dest) in enumerate(arc_identities):
                    if arc_type == "holding":
                        cost = node_db[src].holding_costs.get(comm.asset_type, 0.0)
                    else:
                        edge_obj = network.get_edge(src, dest)
                        cost = edge_obj.costs_per_unit.get(comm.asset_type, 0.0)
                    
                    cpp_arcs[arc_idx].cost = cost

                pricing_engine = fbp.PricingEngine(len(node_indexer), cpp_arcs)
                new_columns = pricing_engine.find_columns([cpp_commodities[comm_idx]], dual_w, dual_alpha)
                new_columns_total.extend(new_columns)

            if not new_columns_total:
                if not filter_active:
                    break
                else:
                    continue 

            for col in new_columns_total:
                if col.arc_ids in path_tracking[col.commodity_id]:
                    continue
                
                comm_obj = network.commodities[col.commodity_id]
                unit_path_cost = 0.0
                
                for arc_id in col.arc_ids:
                    arc_type, src, dest = arc_identities[arc_id]
                    if arc_type == "holding":
                        unit_path_cost += node_db[src].holding_costs.get(comm_obj.asset_type, 0.0)
                    else:
                        unit_path_cost += network.get_edge(src, dest).costs_per_unit.get(comm_obj.asset_type, 0.0)

                # Scale path metrics by volume bulk logic
                total_path_cost = unit_path_cost * comm_obj.volume
                capacity_consumed = comm_obj.volume * comm_obj.consumption_factor

                var = self.solver.NumVar(0.0, self.solver.infinity(), f"path_iter{iteration}_c{col.commodity_id}_{len(lambda_vars)}")
                
                objective.SetCoefficient(var, total_path_cost)
                convexity_constraints[col.commodity_id].SetCoefficient(var, 1.0)
                
                for arc_id in col.arc_ids:
                    capacity_constraints[arc_id].SetCoefficient(var, capacity_consumed)
                
                lambda_vars.append(var)
                path_var_map[var] = col.arc_ids
                path_tracking[col.commodity_id].append(col.arc_ids)

            iteration += 1

        self.solver.Solve()
        return {
            "status": "OPTIMAL" if iteration < max_iterations else "ITERATION_LIMIT",
            "objective_value": objective.Value(),
            "iterations": iteration
        }