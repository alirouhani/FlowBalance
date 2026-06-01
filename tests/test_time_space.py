import pytest
from flowbalance.core.entities import Commodity, Node, Edge, Network
from flowbalance.expander.time_space import TimeSpaceExpander

@pytest.fixture
def sample_network():
    """Generates a structured multi-period network fixture."""
    nodes = [Node(id="Montreal"), Node(id="Toronto")]
    edges = [Edge(from_node="Montreal", to_node="Toronto", transit_time=2)]
    commodities = [
        Commodity(
            id="Shipment_01", asset_type="20FT", origin="Montreal", destination="Toronto",
            volume=15.0, available_time=0, due_date=3
        )
    ]
    return Network(nodes=nodes, edges=edges, commodities=commodities)

def test_time_expanded_arc_generation(sample_network):
    """Verifies the exact structural count of holding and transit arcs given a horizon."""
    # Set time horizon to 4 (Indices: 0, 1, 2, 3)
    expander = TimeSpaceExpander(sample_network, horizon=4)
    arcs = expander.build_time_expanded_arcs()
    
    # 1. Holding arcs: 2 nodes * 3 intervals (0->1, 1->2, 2->3) = 6 arcs
    # 2. Transit arcs: 1 edge with a transit time of 2. 
    #    Can depart at t=0 (arrives 2) and t=1 (arrives 3). Total = 2 arcs
    # Grand Total should equal 8 arcs
    assert len(arcs) == 8
    
    # Explicitly check that no transit arcs depart at t=2 because they would arrive out-of-horizon at t=4
    transit_at_t2 = [a for a in arcs if a[0] == "Montreal" and a[2] == 2 and a[4] == "transit"]
    assert len(transit_at_t2) == 0

def test_commodity_rhs_injection_vectors(sample_network):
    """Verifies that the b-vector precisely maps fluid injections and drains across coordinates."""
    expander = TimeSpaceExpander(sample_network, horizon=4)
    b = expander.compute_commodity_rhs()
    
    # Positive supply faucet (+volume) at source node on available time
    assert b[("Montreal", "Shipment_01", 0)] == 15.0
    
    # Negative demand drain (-volume) at destination node on due date
    assert b[("Toronto", "Shipment_01", 3)] == -15.0
    
    # Verify that flow neutral time steps match 0.0 exactly
    assert b[("Montreal", "Shipment_01", 1)] == 0.0
    assert b[("Toronto", "Shipment_01", 0)] == 0.0