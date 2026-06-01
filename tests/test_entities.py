import pytest
from flowbalance.core.entities import Commodity, Node, Edge, Network

def test_commodity_timeline_validation():
    """Ensures a commodity cannot be created with a due date prior to its available time."""
    with pytest.raises(ValueError, match="due_date cannot be earlier than available_time"):
        Commodity(
            id="Order_Error",
            asset_type="20FT",
            origin="A",
            destination="B",
            volume=10.0,
            available_time=4,
            due_date=2  # Invalid backward time-travel
        )

def test_network_relational_integrity_pass():
    """Verifies that a valid network configuration passes relational validation smoothly."""
    node_a = Node(id="A", capacity_limit=100.0)
    node_b = Node(id="B", capacity_limit=200.0)
    edge = Edge(from_node="A", to_node="B", transit_time=1)
    comm = Commodity(
        id="C1", asset_type="USD", origin="A", destination="B", 
        volume=50.0, available_time=0, due_date=2
    )
    
    network = Network(nodes=[node_a, node_b], edges=[edge], commodities=[comm])
    assert len(network.nodes) == 2
    assert network.commodities[0].id == "C1"

def test_network_invalid_edge_nodes():
    """Ensures that an edge referencing a non-existent node throws an integrity error."""
    node_a = Node(id="A")
    # Edge points to a ghost node "Z"
    bad_edge = Edge(from_node="A", to_node="Z", transit_time=1)
    
    with pytest.raises(ValueError, match="references a non-existent node"):
        Network(nodes=[node_a], edges=[bad_edge], commodities=[])

def test_network_invalid_commodity_nodes():
    """Ensures that a commodity originating from an unregistered node is blocked."""
    node_a = Node(id="A")
    node_b = Node(id="B")
    # Commodity references an unregistered origin "C"
    bad_comm = Commodity(
        id="C1", asset_type="EUR", origin="C", destination="B", 
        volume=10.0, available_time=0, due_date=1
    )
    
    with pytest.raises(ValueError, match="references an invalid origin"):
        Network(nodes=[node_a, node_b], edges=[], commodities=[bad_comm])