import pytest
import pandas as pd
from flowbalance.loader import PandasLoader
from flowbalance.solver import ORToolsNetworkSolver
from flowbalance.analytics import SolutionExporter

def test_solver_capacity_bottleneck_dropping():
    """Tests if the elastic variable y^k drops volume when edge capacity is exceeded."""
    df_nodes = pd.DataFrame([
        {"id": "MTL", "capacity_limit": 100.0, "holding_costs": "{'20FT': 1.0}"},
        {"id": "TOR", "capacity_limit": 100.0, "holding_costs": "{'20FT': 1.0}"}
    ])
    
    df_edges = pd.DataFrame([
        # Force a tight capacity upper bound of 10.0 units
        {"from_node": "MTL", "to_node": "TOR", "transit_time": 1, "shared_capacity_limit": 10.0}
    ])
    
    df_commodities = pd.DataFrame([
        # Order requests 25.0 units -> Overloads the 10.0 edge constraint limit!
        {"id": "Massive_Order", "asset_type": "20FT", "origin": "MTL", "destination": "TOR", "volume": 25.0, "available_time": 0, "due_date": 1}
    ])
    
    network = PandasLoader(df_nodes, df_edges, df_commodities).load_network()
    solver = ORToolsNetworkSolver()
    
    # Execute the solver optimization matrix
    results = solver.solve(network, horizon=2, unfulfillment_penalty=1000.0)
    
    assert results["status"] == "OPTIMAL"
    
    # The solver should have used the y^k drop variable instead of crashing with INFEASIBLE
    assert "Massive_Order" in results["unfulfilled_demand"]
    
    # Process analytics validation
    exporter = SolutionExporter(results)
    df_flows = exporter.to_flow_dataframe()
    df_drops = exporter.to_unfulfilled_dataframe(network.commodities)
    
    # The active allocated transit flow variable should exactly hit the physical capacity limit of 10.0
    transit_flow = df_flows[df_flows["activity"] == "Transit"]["allocated_volume"].sum()
    assert transit_flow == 10.0
    
    # The dropped shortage report should accurately state that 15.0 units were lost
    assert df_drops.loc[0, "lost_volume"] == 15.0