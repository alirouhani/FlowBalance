import pandas as pd
from typing import Dict, Any, List

class SolutionExporter:
    def __init__(self, solver_results: Dict[str, Any]):
        """
        Processes optimization result matrices into analyst-friendly data structures.
        
        Args:
            solver_results (Dict[str, Any]): The exact dictionary output from ORToolsNetworkSolver.
        """
        self.status = solver_results.get("status", "UNKNOWN")
        self.objective_value = solver_results.get("objective_value")
        self.raw_flows = solver_results.get("flows", {})
        self.raw_unfulfilled = solver_results.get("unfulfilled_demand", {})

    def to_flow_dataframe(self) -> pd.DataFrame:
        """
        Flattens the active multidimensional time-space coordinate flows 
        into a clean tabular Pandas DataFrame.
        """
        if self.status != "OPTIMAL" or not self.raw_flows:
            return pd.DataFrame() # Return empty DataFrame if optimization failed

        records: List[Dict[str, Any]] = []
        
        for arc_key, volume in self.raw_flows.items():
            u, ts, v, te, comm_id = arc_key
            
            # Determine operational activity purely by coordinate translation
            activity_type = "Holding" if u == v else "Transit"
            
            records.append({
                "commodity_id": comm_id,
                "origin_node": u,
                "departure_time": ts,
                "destination_node": v,
                "arrival_time": te,
                "duration": te - ts,
                "activity": activity_type,
                "allocated_volume": round(volume, 4)
            })

        df = pd.DataFrame(records)
        # Sort chronologically by departure timeline for a logical flow sequence
        return df.sort_values(by=["commodity_id", "departure_time"]).reset_index(drop=True)

    def to_unfulfilled_dataframe(self, network_commodities: List[Any]) -> pd.DataFrame:
        """
        Compiles a targeted report isolating which orders were dropped due to capacity bottlenecks,
        converting fractions back into absolute volumetric shortages.
        """
        if not self.raw_unfulfilled:
            return pd.DataFrame(columns=["commodity_id", "total_volume", "dropped_fraction", "lost_volume"])

        comm_volumes = {c.id: c.volume for c in network_commodities}
        records: List[Dict[str, Any]] = []

        for comm_id, drop_fraction in self.raw_unfulfilled.items():
            total_vol = comm_volumes.get(comm_id, 0.0)
            records.append({
                "commodity_id": comm_id,
                "total_volume": total_vol,
                "dropped_fraction": round(drop_fraction, 4),
                "lost_volume": round(total_vol * drop_fraction, 4)
            })

        return pd.DataFrame(records).sort_values(by="lost_volume", ascending=False).reset_index(drop=True)