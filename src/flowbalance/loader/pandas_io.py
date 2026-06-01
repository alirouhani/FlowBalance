import pandas as pd
from typing import Dict, Any
from .base import BaseLoader
from flowbalance.core.entities import Node, Edge, Commodity, Network

class PandasLoader(BaseLoader):
    def __init__(self, df_nodes: pd.DataFrame, df_edges: pd.DataFrame, df_commodities: pd.DataFrame):
        self.df_nodes = df_nodes
        self.df_edges = df_edges
        self.df_commodities = df_commodities

    def load_network(self) -> Network:
        nodes = []
        for _, row in self.df_nodes.iterrows():
            holding_costs = row.get("holding_costs", {})
            if isinstance(holding_costs, str):
                holding_costs = eval(holding_costs)
                
            # Cast variables explicitly into a dictionary to satisfy the type checker
            node_data: Dict[str, Any] = {
                "id": str(row["id"]),
                "capacity_limit": float(row.get("capacity_limit", float('inf'))),
                "holding_costs": dict(holding_costs)
            }
            nodes.append(Node(**node_data))

        edges = []
        for _, row in self.df_edges.iterrows():
            costs_per_unit = row.get("costs_per_unit", {})
            if isinstance(costs_per_unit, str):
                costs_per_unit = eval(costs_per_unit)

            edge_data: Dict[str, Any] = {
                "from_node": str(row["from_node"]),
                "to_node": str(row["to_node"]),
                "transit_time": int(row["transit_time"]),
                "shared_capacity_limit": float(row.get("shared_capacity_limit", float('inf'))),
                "costs_per_unit": dict(costs_per_unit)
            }
            edges.append(Edge(**edge_data))

        commodities = []
        for _, row in self.df_commodities.iterrows():
            comm_data: Dict[str, Any] = {
                "id": str(row["id"]),
                "asset_type": str(row["asset_type"]),
                "origin": str(row["origin"]),
                "destination": str(row["destination"]),
                "volume": float(row["volume"]),
                "available_time": int(row["available_time"]),
                "due_date": int(row["due_date"]),
                "consumption_factor": float(row.get("consumption_factor", 1.0))
            }
            commodities.append(Commodity(**comm_data))

        return Network(nodes=nodes, edges=edges, commodities=commodities)