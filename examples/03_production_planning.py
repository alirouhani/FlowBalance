import pandas as pd
import flowbalance as fb

def run_production_example():
    print("\nRunning Production Assembly Model...")
    # Nodes: Machine queues. Holding costs act as penalties for Work-In-Progress (WIP) sitting idle.
    df_nodes = pd.DataFrame([
        {"id": "Raw_Materials", "capacity_limit": 1000.0, "holding_costs": "{'Batch': 1.0}"},
        {"id": "Milling_Station", "capacity_limit": 10.0, "holding_costs": "{'Batch': 50.0}"},  # High penalty to prevent bottleneck queues
        {"id": "Finished_Goods", "capacity_limit": 500.0, "holding_costs": "{'Batch': 2.0}"}
    ])

    # Edges: Processing actions. Transit time is the machine cycle time.
    df_edges = pd.DataFrame([
        {"from_node": "Raw_Materials", "to_node": "Milling_Station", "transit_time": 1, "shared_capacity_limit": 10.0, "costs_per_unit": "{'Batch': 100.0}"},
        {"from_node": "Milling_Station", "to_node": "Finished_Goods", "transit_time": 2, "shared_capacity_limit": 10.0, "costs_per_unit": "{'Batch': 50.0}"}
    ])

    # Commodities: Production orders to fulfill customer demand
    df_commodities = pd.DataFrame([
        {"id": "Order_101", "asset_type": "Batch", "origin": "Raw_Materials", "destination": "Finished_Goods", "volume": 5.0, "available_time": 0, "due_date": 4, "consumption_factor": 1.0}
    ])

    network = fb.PandasLoader(df_nodes, df_edges, df_commodities).load_network()
    results = fb.ORToolsNetworkSolver().solve(network, horizon=5)
    
    print(fb.SolutionExporter(results).to_flow_dataframe().to_string())

if __name__ == "__main__":
    run_production_example()