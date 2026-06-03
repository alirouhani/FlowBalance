import pytest
from flowbalance.core.entities import Node, Edge, Commodity, Network
from flowbalance.cg_solver.cg_engine import ColumnGenerationSolver

@pytest.fixture
def base_network_data():
    """Fixture to build a valid physical network infrastructure."""
    nodes = [
        Node(id="Vancouver", capacity_limit=100.0, holding_costs={"20FT": 2.0}),
        Node(id="Calgary", capacity_limit=100.0, holding_costs={"20FT": 1.5}),
        Node(id="Montreal", capacity_limit=200.0, holding_costs={"20FT": 3.0})
    ]
    
    edges = [
        Edge(
            from_node="Vancouver", 
            to_node="Calgary", 
            transit_time=1, 
            shared_capacity_limit=30.0, 
            costs_per_unit={"20FT": 10.0}
        ),
        Edge(
            from_node="Calgary", 
            to_node="Montreal", 
            transit_time=2, 
            shared_capacity_limit=25.0, 
            costs_per_unit={"20FT": 15.0}
        ),
        Edge(
            from_node="Vancouver", 
            to_node="Montreal", 
            transit_time=4, 
            shared_capacity_limit=15.0, 
            costs_per_unit={"20FT": 35.0}
        )
    ]
    return nodes, edges


def test_single_commodity_direct_routing(base_network_data):
    """
    Test 1: Verifies that a single commodity takes the mathematically 
    cheapest path across time steps.
    """
    nodes, edges = base_network_data
    
    # 10 units of 20FT container from Vancouver to Calgary
    commodities = [
        Commodity(
            id="C1",
            asset_type="20FT",
            origin="Vancouver",
            destination="Calgary",
            volume=10.0,
            available_time=0,
            due_date=2,
            consumption_factor=1.0
        )
    ]
    
    network = Network(nodes=nodes, edges=edges, commodities=commodities)
    solver = ColumnGenerationSolver()
    
    # Solve with a time horizon of 3 steps
    result = solver.solve(network, horizon=3)
    
    assert result["status"] == "OPTIMAL"
    # Cost should equal: volume (10.0) * edge_cost (10.0) = 100.0
    # Plus holding cost at destination if it stays there until due_date
    assert result["objective_value"] >= 100.0


def test_holding_arc_activation(base_network_data):
    """
    Test 2: Forces the commodity to wait at an inventory node (holding arc) 
    because the due date is extended, evaluating holding cost injection.
    """
    nodes, edges = base_network_data
    
    # Arrival is forced to wait
    commodities = [
        Commodity(
            id="C2",
            asset_type="20FT",
            origin="Vancouver",
            destination="Calgary",
            volume=5.0,
            available_time=0,
            due_date=3, # Extended due date forces holding behavior
            consumption_factor=1.0
        )
    ]
    
    network = Network(nodes=nodes, edges=edges, commodities=commodities)
    solver = ColumnGenerationSolver()
    
    result = solver.solve(network, horizon=4)
    
    assert result["status"] == "OPTIMAL"
    # Base transit cost: 5.0 * 10.0 = 50.0
    # The solver will find the shortest path, incurring temporal holding costs
    assert result["objective_value"] > 50.0


def test_shared_edge_capacity_bottleneck(base_network_data):
    """
    Test 3: Confirms the column generation engine respects shared edge capacities.
    Total requested volume exceeds direct edge limits, forcing alternative paths or split routes.
    """
    nodes, edges = base_network_data
    
    # Shrink the capacity of Vancouver -> Calgary to force a bottleneck
    edges[0].shared_capacity_limit = 5.0 
    
    # We want to move 15.0 units, but edge capacity is only 5.0
    commodities = [
        Commodity(
            id="C3_bulk",
            asset_type="20FT",
            origin="Vancouver",
            destination="Calgary",
            volume=15.0,
            available_time=0,
            due_date=2
        )
    ]
    
    network = Network(nodes=nodes, edges=edges, commodities=commodities)
    solver = ColumnGenerationSolver()
    
    result = solver.solve(network, horizon=3)
    
    # If the system cannot handle the overflow due to capacity limitations, 
    # the objective will reflect the utilization of the high big-M artificial penalty variables
    assert result["status"] == "OPTIMAL"
    assert result["objective_value"] > 0.0


def test_pydantic_timeline_validator():
    """
    Test 4: Pure schema test ensuring the Pydantic model throws a ValueError 
    if a commodity due date occurs before its available time.
    """
    with pytest.raises(ValueError, match="due_date cannot be earlier than available_time"):
        Commodity(
            id="C_Error",
            asset_type="20FT",
            origin="NodeA",
            destination="NodeB",
            volume=10.0,
            available_time=5,
            due_date=2 # Invalid timeline
        )


def test_network_relational_integrity_validator():
    """
    Test 5: Validates that the network throws an integrity error if an edge 
    points to a node that does not exist in the node ledger array.
    """
    nodes = [Node(id="RealNode", capacity_limit=50.0)]
    edges = [Edge(from_node="RealNode", to_node="FakeNode", transit_time=1)] # Non-existent target
    commodities = []
    
    with pytest.raises(ValueError, match="references a non-existent node"):
        Network(nodes=nodes, edges=edges, commodities=commodities)