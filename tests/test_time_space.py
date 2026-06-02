import pytest
from flowbalance.core.entities import Commodity, Node, Edge, Network
from flowbalance.expander.time_space import TimeSpaceExpander

@pytest.fixture
def sample_network():
    """Generates a structured multi-period network model."""
    nodes = [Node(id="MTL"), Node(id="TOR")]
    edges = [Edge(from_node="MTL", to_node="TOR", transit_time=2)]
    commodities = [
        Commodity(
            id="Order_01", asset_type="20FT", origin="MTL", destination="TOR",
            volume=15.0, available_time=0, due_date=3
        )
    ]
    return Network(nodes=nodes, edges=edges, commodities=commodities)

def test_coordinate_arc_generation(sample_network):
    """Verifies the exact coordinate tuple generation for a given horizon."""
    # Horizon 4: time steps 0, 1, 2, 3
    expander = TimeSpaceExpander(sample_network, horizon=4)
    arcs = expander.build_time_expanded_arcs()
    
    # Expected Holding Arcs: 2 nodes * 3 intervals (0->1, 1->2, 2->3) = 6 arcs
    # Expected Transit Arcs: 1 edge. Can depart at t=0 (arrives 2), t=1 (arrives 3). Total = 2 arcs
    # Grand Total = 8 arcs
    assert len(arcs) == 8
    
    # Assert format is strictly (from_node, from_time, to_node, to_time) without arc_type strings
    for arc in arcs:
        assert len(arc) == 4
        assert isinstance(arc[1], int)
        assert isinstance(arc[3], int)

def test_absolute_volume_rhs_injection(sample_network):
    """Verifies that rhs injections contain the raw volume value instead of flags."""
    expander = TimeSpaceExpander(sample_network, horizon=4)
    b = expander.compute_commodity_rhs()
    
    # Source faucet s^k: must equal +v^k (+15.0)
    assert b[("MTL", 0, "Order_01")] == 15.0
    
    # Sink drain e^k: must equal -v^k (-15.0)
    assert b[("TOR", 3, "Order_01")] == -15.0
    
    # Intermediate non-faucet steps must default to 0.0 or not be in the map
    assert b.get(("MTL", 1, "Order_01"), 0.0) == 0.0