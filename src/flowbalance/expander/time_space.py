from typing import List, Dict, Tuple
from flowbalance.core.entities import Network

class TimeSpaceExpander:
    def __init__(self, network: Network, horizon: int):
        self.network = network
        self.horizon = horizon

    def build_time_expanded_arcs(self) -> List[Tuple[str, str, int, int, str]]:
        """Generates holding and transit arcs across the temporal planning window."""
        expanded_arcs = []
        node_ids = {n.id for n in self.network.nodes}

        for t in range(self.horizon):
            # 1. Holding Arcs (Stay at the same location)
            if t < self.horizon - 1:
                for node_id in node_ids:
                    expanded_arcs.append((node_id, node_id, t, t + 1, "holding"))

            # 2. Transit Arcs (Move between locations)
            for edge in self.network.edges:
                arrival_time = t + edge.transit_time
                if arrival_time < self.horizon:
                    expanded_arcs.append((edge.from_node, edge.to_node, t, arrival_time, "transit"))

        return expanded_arcs

    def compute_commodity_rhs(self) -> Dict[Tuple[str, str, int], float]:
        """
        Compiles the independent RHS matrix vector (b).
        Key: (node_id, commodity_id, time_step) -> Value: net injection
        """
        b: Dict[Tuple[str, str, int], float] = {}

        # Initialize the sparse map to 0.0 for every active node, commodity, and time step
        node_ids = {n.id for n in self.network.nodes}
        for comm in self.network.commodities:
            for node_id in node_ids:
                for t in range(self.horizon):
                    b[(node_id, comm.id, t)] = 0.0

        # Inject the faucets and drains matching your definition
        for comm in self.network.commodities:
            # Source faucet (+volume)
            src_key = (comm.origin, comm.id, comm.available_time)
            if src_key in b:
                b[src_key] += comm.volume

            # Sink drain (-volume)
            sink_key = (comm.destination, comm.id, comm.due_date)
            if sink_key in b:
                b[sink_key] -= comm.volume

        return b