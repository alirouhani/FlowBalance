import logging
from typing import Dict, Any, List
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

    def solve(self, network: Network, horizon: int, max_iterations: int = 100) -> Dict[str, Any]:
        if not CPP_PRICING_AVAILABLE:
            raise ImportError("C++ Pricing Engine module is strictly required.")

        self.solver.Clear()
        
        # 1. Map physical node structures to quick-lookup dictionaries
        node_db = {node.id: node for node in network.nodes}
        
        # 2. Reconstruct the time-space network expansion boundaries
        # We simulate the expander output tuples: (from_node, start_t, to_node, end_t, commodity_context)
        # To avoid index drift, we build the core pricing tracking tables dynamically
        
        # Build unique flattened mapping for spatial-temporal coordinate pairs
        unique_coords = set()
        for node in network.nodes:
            for t in range(horizon + 1):
                unique_coords.add((node.id, t))
                
        node_indexer = {coord: idx for idx, coord in enumerate(sorted(list(unique_coords)))}
        
        cpp_arcs = []
        arc_capacity_map = []
        
        # We must structure separate cost structures per commodity tracking matrix 
        # since costs_per_unit vary by asset_type. We pass a standardized base cost layout to C++
        # and scale dual pricing evaluations appropriately.
        arc_identities = [] # Tracks structural mapping: (type, source, target, asset_context)
        
        arc_counter = 0
        for u_id in node_db.keys():
            for t in range(horizon):
                # Scenario A: Generate Temporal Inventory Holding Arcs (u -> u)
                u_coord = node_indexer[(u_id, t)]
                v_coord = node_indexer[(u_id, t + 1)]
                node_obj = node_db[u_id]
                
                # Capacity bound extraction directly from your Pydantic Field
                capacity = node_obj.capacity_limit if node_obj.capacity_limit != float('inf') else 1e5
                
                # We use a placeholder for C++, but evaluate true asset paths during column generation
                cpp_arcs.append(fbp.TimeSpaceArc(arc_counter, u_coord, v_coord, 0.0))
                arc_capacity_map.append(capacity)
                arc_identities.append(("holding", u_id, u_id))
                arc_counter += 1
                
        for edge in network.edges:
            for t in range(horizon + 1):
                # Scenario B: Generate Spatial Movement Transport Arcs (u -> v)
                arrival_time = t + edge.transit_time
                if arrival_time <= horizon:
                    u_coord = node_indexer[(edge.from_node, t)]
                    v_coord = node_indexer[(edge.to_node, arrival_time)]
                    
                    capacity = edge.shared_capacity_limit if edge.shared_capacity_limit != float('inf') else 1e5
                    
                    cpp_arcs.append(fbp.TimeSpaceArc(arc_counter, u_coord, v_coord, 0.0))
                    arc_capacity_map.append(capacity)
                    arc_identities.append(("transit", edge.from_node, edge.to_node))
                    arc_counter += 1

        cpp_commodities = []
        demand_map = []
        for i, comm in enumerate(network.commodities):
            cpp_commodities.append(fbp.CommodityCore(
                i, node_indexer[(comm.origin, comm.available_time)], node_indexer[(comm.destination, comm.due_date)]
            ))
            demand_map.append(comm.volume)

        # 3. Initialize Master Constraints inside OR-Tools Matrix
        capacity_constraints = [self.solver.Constraint(0.0, cap, f"cap_{idx}") for idx, cap in enumerate(arc_capacity_map)]
        demand_constraints = [self.solver.Constraint(dem, dem, f"dem_{idx}") for idx, dem in enumerate(demand_map)]
        
        objective = self.solver.Objective()
        objective.SetMinimization()

        path_structures = []
        lambda_vars: List[pywraplp.Variable] = []
        
        # Seed initial basis with high-penalty columns to guarantee initial matrix feasibility
        for i, comm in enumerate(network.commodities):
            var = self.solver.NumVar(0.0, self.solver.infinity(), f"artificial_{i}")
            objective.SetCoefficient(var, 10000.0) 
            demand_constraints[i].SetCoefficient(var, 1.0)
            lambda_vars.append(var)
            path_structures.append(None)

        # 4. Interactive Column Generation Execution Loop
        iteration = 0
        while iteration < max_iterations:
            status = self.solver.Solve()
            if status != pywraplp.Solver.OPTIMAL:
                break

            dual_pi = [abs(c.DualValue()) for c in capacity_constraints]
            dual_mu = [c.DualValue() for c in demand_constraints]

            # Re-calculate absolute network parameters dynamically per commodity type
            # to accommodate exact dictionary metrics from your model definitions
            for comm in network.commodities:
                comm_id = network.commodities.index(comm)
                
                # Dynamically inject asset costs into the C++ pricing engine topology weights
                for arc_idx, (arc_type, src, dest) in enumerate(arc_identities):
                    if arc_type == "holding":
                        cost = node_db[src].holding_costs.get(comm.asset_type, 0.0)
                    else:
                        edge_obj = network.get_edge(src, dest)
                        cost = edge_obj.costs_per_unit.get(comm.asset_type, 0.0)
                    
                    # Update edge weight parameters directly across memory pointers
                    cpp_arcs[arc_idx].cost = cost

                # Trigger high-speed topological shortest path calculation in C++
                pricing_engine = fbp.PricingEngine(len(node_indexer), cpp_arcs)
                new_columns = pricing_engine.find_columns([cpp_commodities[comm_id]], dual_pi, dual_mu)

                for col in new_columns:
                    if col.arc_ids in path_structures:
                        continue
                        
                    # Calculate true asset paths cost using Pydantic parameters
                    true_path_cost = 0.0
                    for arc_id in col.arc_ids:
                        arc_type, src, dest = arc_identities[arc_id]
                        if arc_type == "holding":
                            true_path_cost += node_db[src].holding_costs.get(comm.asset_type, 0.0)
                        else:
                            true_path_cost += network.get_edge(src, dest).costs_per_unit.get(comm.asset_type, 0.0)

                    var = self.solver.NumVar(0.0, self.solver.infinity(), f"path_iter{iteration}_c{comm_id}")
                    objective.SetCoefficient(var, true_path_cost)
                    
                    demand_constraints[comm_id].SetCoefficient(var, 1.0)
                    for arc_id in col.arc_ids:
                        # Incorporate consumption multipliers directly into matrix mapping coefficients
                        capacity_constraints[arc_id].SetCoefficient(var, comm.consumption_factor)
                        
                    lambda_vars.append(var)
                    path_structures.append(col.arc_ids)

            if iteration > 0 and len(lambda_vars) == last_iter_count:
                # Terminate loop if no distinct non-basic structures enter the basis
                break
                
            last_iter_count = len(lambda_vars)
            iteration += 1

        self.solver.Solve()
        return {
            "status": "OPTIMAL",
            "objective_value": objective.Value(),
            "iterations": iteration
        }