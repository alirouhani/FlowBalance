import collections
from typing import Dict, Any, Tuple
from ortools.linear_solver import pywraplp
from flowbalance.solver.base import BaseSolver
from flowbalance.core.entities import Network
from flowbalance.expander.time_space import TimeSpaceExpander

class ORToolsNetworkSolver(BaseSolver):
    def __init__(self):
        self.solver = pywraplp.Solver.CreateSolver('GLOP')
        if not self.solver:
            raise RuntimeError("Google OR-Tools GLOP backend failed to initialize.")

    def solve(self, network: Network, horizon: int, unfulfillment_penalty: float = 1e6) -> Dict[str, Any]:
        self.solver.Clear()
        
        # 1. Topological Expansion
        expander = TimeSpaceExpander(network, horizon)
        expanded_arcs = expander.build_time_expanded_arcs()
        rhs_map = expander.compute_commodity_rhs()

        commodities_map = {c.id: c for c in network.commodities}

        # 2. Decision Variables
        # x: Flow variables -> x[(from_node, from_time, to_node, to_time, comm_id)]
        x: Dict[Tuple[str, int, str, int, str], pywraplp.Variable] = {}
        y: Dict[str, pywraplp.Variable] = {}

        for comm_id in commodities_map.keys():
            y[comm_id] = self.solver.NumVar(0.0, 1.0, f"unfulfilled_{comm_id}")
            
            for arc in expanded_arcs:
                u, ts, v, te = arc
                var_name = f"flow_{u}_{ts}_{v}_{te}_{comm_id}"
                x[(u, ts, v, te, comm_id)] = self.solver.NumVar(0.0, self.solver.infinity(), var_name)

        # 3. Objective Function
        objective = self.solver.Objective()
        objective.SetMinimization()

        node_holding_costs = {n.id: n.holding_costs for n in network.nodes}
        edge_transit_costs = {(e.from_node, e.to_node): e.costs_per_unit for e in network.edges}

        # Apply operational costs dynamically based on coordinates
        for arc_key, var in x.items():
            u, ts, v, te, comm_id = arc_key
            asset = commodities_map[comm_id].asset_type
            cost_coeff = 0.0

            if u == v: # Coordinates are at the same physical location -> Holding
                cost_coeff = node_holding_costs.get(u, {}).get(asset, 0.0)
            else:      # Coordinates move between locations -> Transit
                cost_coeff = edge_transit_costs.get((u, v), {}).get(asset, 0.0)

            if cost_coeff != 0.0:
                objective.SetCoefficient(var, cost_coeff)

        for comm_id, y_var in y.items():
            volume = commodities_map[comm_id].volume
            objective.SetCoefficient(y_var, unfulfillment_penalty * volume)

        outgoing_arcs = collections.defaultdict(list)
        incoming_arcs = collections.defaultdict(list)
        for arc in expanded_arcs:
            u, ts, v, te = arc
            outgoing_arcs[(u, ts)].append(arc)
            incoming_arcs[(v, te)].append(arc)

        # Guarantee all spatial locations with demand are evaluated, even if disconnected
        coordinates = set(outgoing_arcs.keys()).union(set(incoming_arcs.keys()))
        for rhs_key in rhs_map.keys():
            node, t, _ = rhs_key
            coordinates.add((node, t))

        # 4. Mass Balance Constraints
        for comm_id in commodities_map.keys():
            for coord in coordinates:
                node, t = coord
                
                rhs_val = rhs_map.get((node, t, comm_id), 0.0)
                
                # Neutralize constraint generation for mathematically inert coordinates
                if rhs_val == 0.0 and not outgoing_arcs[coord] and not incoming_arcs[coord]:
                    continue

                constraint = self.solver.Constraint(rhs_val, rhs_val, f"bal_{node}_{t}_{comm_id}")
                
                if rhs_val != 0.0:
                    constraint.SetCoefficient(y[comm_id], rhs_val)

                for arc in outgoing_arcs[coord]:
                    u, ts, v, te = arc
                    constraint.SetCoefficient(x[(u, ts, v, te, comm_id)], 1.0)

                for arc in incoming_arcs[coord]:
                    u, ts, v, te = arc
                    constraint.SetCoefficient(x[(u, ts, v, te, comm_id)], -1.0)

        # 5. Shared Edge Capacity Constraints
        edge_capacity_limits = {(e.from_node, e.to_node): e.shared_capacity_limit for e in network.edges}
        
        for edge in network.edges:
            capacity = edge_capacity_limits[(edge.from_node, edge.to_node)]
            if capacity == float('inf'):
                continue 

            for t in range(horizon):
                t_bar = t + edge.transit_time
                
                # Prune capacity row generation if the temporal transit exceeds the allowed horizon
                if t_bar >= horizon:
                    continue

                cap_constraint = self.solver.Constraint(0.0, capacity, f"cap_{edge.from_node}_{edge.to_node}_{t}")
                has_vars = False
                
                for comm_id in commodities_map.keys():
                    arc_key = (edge.from_node, t, edge.to_node, t_bar, comm_id)
                    if arc_key in x:
                        alpha = commodities_map[comm_id].consumption_factor
                        cap_constraint.SetCoefficient(x[arc_key], alpha)
                        has_vars = True
                        
                if not has_vars:
                    cap_constraint.SetBounds(-self.solver.infinity(), self.solver.infinity())

        status = self.solver.Solve()

        # 6. Extract Results
        results: Dict[str, Any] = {
            "status": "UNKNOWN",
            "objective_value": None,
            "flows": {},
            "unfulfilled_demand": {}
        }

        if status == pywraplp.Solver.OPTIMAL:
            results["status"] = "OPTIMAL"
            results["objective_value"] = objective.Value()
            
            for arc, var in x.items():
                val = var.solution_value()
                if val > 1e-6: 
                    results["flows"][arc] = val
            
            for comm_id, y_var in y.items():
                drop_fraction = y_var.solution_value()
                if drop_fraction > 1e-6:
                    results["unfulfilled_demand"][comm_id] = drop_fraction
            
        elif status == pywraplp.Solver.INFEASIBLE:
            results["status"] = "INFEASIBLE"

        return results