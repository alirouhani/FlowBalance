import pandas as pd
from flowbalance.loader import PandasLoader
from flowbalance.solver import ORToolsNetworkSolver
from flowbalance.analytics import SolutionExporter

# 1. Ingest flat data where demand deliberately exceeds capacity to trigger y^k
df_nodes = pd.DataFrame([
    {"id": "Montreal", "capacity_limit": 500.0, "holding_costs": "{'20FT': 2.0}"},
    {"id": "Toronto", "capacity_limit": 500.0, "holding_costs": "{'20FT': 5.0}"}
])

df_edges = pd.DataFrame([
    # Strictly bottlenecking capacity down to 15.0 units max transit per step
    {"from_node": "Montreal", "to_node": "Toronto", "transit_time": 2, "shared_capacity_limit": 15.0, "costs_per_unit": "{'20FT': 20.0}"}
])

df_commodities = pd.DataFrame([
    # Total volume combined = 25.0 (This will overload the 15.0 edge limit!)
    {"id": "High_PriorityP_Order", "asset_type": "20FT", "origin": "Montreal", "destination": "Toronto", "volume": 15.0, "available_time": 0, "due_date": 3, "consumption_factor": 1.0},
    {"id": "Low_Priority_Order", "asset_type": "20FT", "origin": "Montreal", "destination": "Toronto", "volume": 10.0, "available_time": 0, "due_date": 3, "consumption_factor": 1.0}
])

# 2. Pipeline execution
network = PandasLoader(df_nodes, df_edges, df_commodities).load_network()
solver = ORToolsNetworkSolver()
results = solver.solve(network, horizon=4, unfulfillment_penalty=5000.0)

# 3. Process outputs into analytics reports
exporter = SolutionExporter(results)
df_flows = exporter.to_flow_dataframe()
df_bottlenecks = exporter.to_unfulfilled_dataframe(network.commodities)

# --- TELEMETRY DASHBOARD OUTPUT ---
print(f"Optimization Status: {results['status']}")
print(f"Total Combined Cost matrix: ${results['objective_value']}\n")

print("=== OPTIMIZED NETWORK ROUTING SCHEDULE ===")
print(df_flows.to_string())

print("\n=== SYSTEM BOTTLENECK & DROPPED DEMAND REPORT ===")
if df_bottlenecks.empty:
    print("Perfect execution. Zero unfulfilled items.")
else:
    print(df_bottlenecks.to_string())