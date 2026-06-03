import pandas as pd
import flowbalance as fb

def run_finance_example():
    print("\nRunning Liquidity Transfer Model...")
    # Nodes: Corporate Bank Accounts.
    # Holding cost = Opportunity cost. High cost in un-invested operational accounts.
    df_nodes = pd.DataFrame([
        {"id": "Global_Treasury", "capacity_limit": float('inf'), "holding_costs": "{'USD_Millions': 0.0}"}, 
        {"id": "EU_Subsidiary", "capacity_limit": float('inf'), "holding_costs": "{'USD_Millions': 5.0}"},
        {"id": "APAC_Subsidiary", "capacity_limit": float('inf'), "holding_costs": "{'USD_Millions': 8.0}"}
    ])

    # Edges: Wire transfers. Transit time is the clearing period (e.g., T+2 settlement).
    df_edges = pd.DataFrame([
        {"from_node": "Global_Treasury", "to_node": "EU_Subsidiary", "transit_time": 1, "shared_capacity_limit": 50.0, "costs_per_unit": "{'USD_Millions': 0.1}"},
        {"from_node": "Global_Treasury", "to_node": "APAC_Subsidiary", "transit_time": 2, "shared_capacity_limit": 20.0, "costs_per_unit": "{'USD_Millions': 0.5}"}
    ])

    # Commodities: Targeted cash injections required for payroll or tax obligations
    df_commodities = pd.DataFrame([
        {"id": "EU_Payroll", "asset_type": "USD_Millions", "origin": "Global_Treasury", "destination": "EU_Subsidiary", "volume": 15.0, "available_time": 0, "due_date": 2, "consumption_factor": 1.0},
        {"id": "APAC_Tax", "asset_type": "USD_Millions", "origin": "Global_Treasury", "destination": "APAC_Subsidiary", "volume": 8.0, "available_time": 0, "due_date": 3, "consumption_factor": 1.0}
    ])

    network = fb.PandasLoader(df_nodes, df_edges, df_commodities).load_network()
    # High penalty ensures we prioritize meeting payroll over keeping cash in the treasury
    results = fb.ORToolsNetworkSolver().solve(network, horizon=4, unfulfillment_penalty=10000.0)
    
    print(fb.SolutionExporter(results).to_flow_dataframe().to_string())
    print(fb.SolutionExporter(results).objective_value)
    print(fb.ColumnGenerationSolver().solve(network, horizon=6))    

if __name__ == "__main__":
    run_finance_example()