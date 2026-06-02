import pandas as pd
import flowbalance as fb

def run_logistics_example():
    print("Running Logistics Routing Model...")
    # Nodes: Physical cities. Holding costs represent warehousing fees.
    df_nodes = pd.DataFrame([
        {"id": "Vancouver", "capacity_limit": 500.0, "holding_costs": "{'Electronics': 5.0}"},
        {"id": "Calgary", "capacity_limit": 200.0, "holding_costs": "{'Electronics': 2.0}"},
        {"id": "Toronto", "capacity_limit": 500.0, "holding_costs": "{'Electronics': 5.0}"}
    ])

    # Edges: Transportation lanes. Transit times are days on the road.
    df_edges = pd.DataFrame([
        {"from_node": "Vancouver", "to_node": "Calgary", "transit_time": 1, "shared_capacity_limit": 50.0, "costs_per_unit": "{'Electronics': 20.0}"},
        {"from_node": "Calgary", "to_node": "Toronto", "transit_time": 3, "shared_capacity_limit": 100.0, "costs_per_unit": "{'Electronics': 40.0}"},
        # Direct express flight alternative (Faster but expensive, low capacity)
        {"from_node": "Vancouver", "to_node": "Toronto", "transit_time": 1, "shared_capacity_limit": 10.0, "costs_per_unit": "{'Electronics': 150.0}"}
    ])

    # Commodities: Customer orders with strict due dates
    df_commodities = pd.DataFrame([
        {"id": "Tech_Shipment_A", "asset_type": "Electronics", "origin": "Vancouver", "destination": "Toronto", "volume": 30.0, "available_time": 0, "due_date": 4, "consumption_factor": 1.0}
    ])

    network = fb.PandasLoader(df_nodes, df_edges, df_commodities).load_network()
    results = fb.ORToolsNetworkSolver().solve(network, horizon=6)
    
    print(fb.SolutionExporter(results).to_flow_dataframe().to_string())

if __name__ == "__main__":
    run_logistics_example()