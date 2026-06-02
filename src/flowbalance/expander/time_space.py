from typing import List, Dict, Tuple
from flowbalance.core.entities import Network

# Attempt to load the blazing-fast C++ backend
try:
    import _flowbalance_cpp
    C_BACKEND_AVAILABLE = True
except ImportError:
    C_BACKEND_AVAILABLE = False
    print("Warning: C++ backend not found. Falling back to pure Python loop execution.")

class TimeSpaceExpander:
    def __init__(self, network: Network, horizon: int):
        self.network = network
        self.horizon = horizon

    def build_time_expanded_arcs(self) -> List[Tuple[str, int, str, int]]:
        """
        Constructs the complete set of unified directed time-space arcs.
        Returns a list of tuples formatted as: (from_location, from_time, to_location, to_time)
        """
        if C_BACKEND_AVAILABLE:
            return _flowbalance_cpp.build_arcs(self.horizon, self.network.nodes, self.network.edges)
        
        expanded_arcs: List[Tuple[str, int, str, int]] = []
        
        # 1. Pure Python Fallback: Temporal Holding Arcs -> ((i, t), (i, t+1))
        for t in range(self.horizon - 1):
            for node in self.network.nodes:
                expanded_arcs.append((node.id, t, node.id, t + 1))
                
        # 2. Pure Python Fallback: Physical Transit Arcs -> ((i, t), (j, t_bar))
        for t in range(self.horizon):
            for edge in self.network.edges:
                t_bar = t + edge.transit_time
                if t_bar < self.horizon:
                    expanded_arcs.append((edge.from_node, t, edge.to_node, t_bar))
                    
        return expanded_arcs

    def compute_commodity_rhs(self) -> Dict[Tuple[str, int, str], float]:
        """
        Compiles absolute demand injection vectors across discrete time-space nodes.
        Returns a dictionary mapped as: {(location, time, commodity_id): volume}
        """
        if C_BACKEND_AVAILABLE:
            return _flowbalance_cpp.compute_rhs(self.horizon, self.network.commodities)
        
        b: Dict[Tuple[str, int, str], float] = {}
        
        for comm in self.network.commodities:
            # Source coordinate injection (s^k) -> +v^k
            source_key = (comm.origin, comm.available_time, comm.id)
            b[source_key] = b.get(source_key, 0.0) + comm.volume
            
            # Sink coordinate extraction (e^k) -> -v^k
            sink_key = (comm.destination, comm.due_date, comm.id)
            b[sink_key] = b.get(sink_key, 0.0) - comm.volume
            
        return b