import pandas as pd
import flowbalance as fb

def run_inventory_example():
    print("\nRunning Multi-Echelon Inventory Model...")
    # Nodes: Supply chain echelons. Factory is expensive to hold stock, DC is cheap.
    df_nodes = pd.DataFrame([
        {"id": "Factory", "capacity_limit": 1000.0, "holding_costs": "{'Pallet': 15.0}"},
        {"id": "Regional_DC", "capacity_limit": 5000.0, "holding_costs": "{'Pallet': 2.0}"},
        {"id": "Retail_Store", "capacity_limit": 100.0, "holding_costs": "{'Pallet': 8.0}"}
    ])

    # Edges: Internal logistics transfers
    df_edges = pd.DataFrame([
        {"from_node": "Factory", "to_node": "Regional_DC", "transit_time": 2, "shared_capacity_limit": 200.0, "costs_per_unit": "{'Pallet': 5.0}"},
        {"from_node": "Regional_DC", "to_node": "Retail_Store", "transit_time": 1, "shared_capacity_limit": 50.0, "costs_per_unit": "{'Pallet': 10.0}"}
    ])

    # Commodities: Target stock levels required at the retail store on specific days
    df_commodities = pd.DataFrame([
        {"id": "Weekend_Restock", "asset_type": "Pallet", "origin": "Factory", "destination": "Retail_Store", "volume": 40.0, "available_time": 0, "due_date": 4, "consumption_factor": 1.0},
        {"id": "Midweek_Promo", "asset_type": "Pallet", "origin": "Factory", "destination": "Retail_Store", "volume": 20.0, "available_time": 1, "due_date": 3, "consumption_factor": 1.0}
    ])

    network = fb.PandasLoader(df_nodes, df_edges, df_commodities).load_network()
    results = fb.ORToolsNetworkSolver().solve(network, horizon=6)
    
    print(fb.SolutionExporter(results).to_flow_dataframe().to_string())

if __name__ == "__main__":
    run_inventory_example()