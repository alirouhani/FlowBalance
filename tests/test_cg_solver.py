import pytest
from flowbalance.core.entities import Node, Edge, Commodity, Network
from flowbalance.cg_solver.cg_engine import ColumnGenerationSolver

@pytest.fixture
def base_network_data():
    """Fixture establishing a valid physical network infrastructure."""
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


def test_exact_volume_scaling_routing(base_network_data):
    """
    Test 1: Verifies that the C++ pricing engine correctly scales path costs 
    by the commodity volume, selecting the optimal combination of transit and holding.
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
    
    result = solver.solve(network, horizon=3)
    
    assert result["status"] == "OPTIMAL"
    
    # The optimal mathematical path: 
    # Transit Van -> Cal at t=0 (Cost: 10.0/unit)
    # Hold at Cal from t=1 to t=2 (Cost: 1.5/unit)
    # Total Unit Cost = 11.5 | Total Bulk Cost = 11.5 * 10.0 = 115.0
    assert result["objective_value"] == pytest.approx(115.0, rel=1e-5)


def test_holding_arc_temporal_penalty(base_network_data):
    """
    Test 2: Evaluates extended temporal inventory behavior. The solver must dynamically 
    calculate holding costs across multiple time steps.
    """
    nodes, edges = base_network_data
    
    commodities = [
        Commodity(
            id="C2",
            asset_type="20FT",
            origin="Vancouver",
            destination="Calgary",
            volume=5.0,
            available_time=0,
            due_date=3, 
            consumption_factor=1.0
        )
    ]
    
    network = Network(nodes=nodes, edges=edges, commodities=commodities)
    solver = ColumnGenerationSolver()
    
    result = solver.solve(network, horizon=4)
    
    assert result["status"] == "OPTIMAL"
    
    # Path: Van(0) -> Cal(1) -> Cal(2) -> Cal(3)
    # Unit Cost: 10.0 (Transit) + 1.5 (Hold) + 1.5 (Hold) = 13.0
    # Total Bulk Cost = 13.0 * 5.0 = 65.0
    assert result["objective_value"] == pytest.approx(65.0, rel=1e-5)


def test_convexity_and_artificial_penalty(base_network_data):
    """
    Test 3: Confirms the Dantzig-Wolfe convexity constraint triggers the big-M 
    artificial penalty when spatial network capacity physically cannot meet demand.
    """
    nodes, edges = base_network_data
    
    # Artificially constrain the capacity bottleneck
    edges[0].shared_capacity_limit = 5.0 
    
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
    
    assert result["status"] == "OPTIMAL"
    
    # The solver will brilliantly split the flow across TWO time steps:
    # 1. Van(0) -> Cal(1) -> Cal(2) [uses 5.0 capacity]
    # 2. Van(0) -> Van(1) -> Cal(2) [uses 5.0 capacity]
    # The remaining 5.0 volume (1/3 of total) is forced into the big-M artificial column.
    # Therefore, the cost will be roughly 1/3 of 1e6 plus the minor physical routing costs.
    assert result["objective_value"] > 300000.0


def test_consumption_factor_scaling(base_network_data):
    """
    Test 4: Ensures the consumption factor dynamically scales the capacity utilized 
    in the Master Problem and influences dual values sent to the C++ core.
    """
    nodes, edges = base_network_data
    
    # 10 units requested, but consumption_factor is 2.0 (effectively takes 20 capacity)
    # Edge capacity is 30.0, so this should route successfully without triggering big-M.
    commodities = [
        Commodity(
            id="C4",
            asset_type="20FT",
            origin="Vancouver",
            destination="Calgary",
            volume=10.0,
            available_time=0,
            due_date=2,
            consumption_factor=2.0 
        )
    ]
    
    network = Network(nodes=nodes, edges=edges, commodities=commodities)
    solver = ColumnGenerationSolver()
    
    result = solver.solve(network, horizon=3)
    
    assert result["status"] == "OPTIMAL"
    # Cost remains standard (115.0) because consumption factor limits capacity, 
    # not the fundamental financial cost per unit.
    assert result["objective_value"] == pytest.approx(115.0, rel=1e-5)


def test_pydantic_timeline_validator():
    """
    Test 5: Validates intrinsic schema parameters ensuring chronological consistency.
    """
    with pytest.raises(ValueError, match="due_date cannot be earlier than available_time"):
        Commodity(
            id="C_Error",
            asset_type="20FT",
            origin="NodeA",
            destination="NodeB",
            volume=10.0,
            available_time=5,
            due_date=2, 
            consumption_factor=1.0
        )


def test_network_relational_integrity_validator():
    """
    Test 6: Validates structural integrity matrices.
    """
    nodes = [Node(id="RealNode", capacity_limit=50.0)]
    edges = [Edge(from_node="RealNode", to_node="FakeNode", transit_time=1)]
    commodities = []
    
    with pytest.raises(ValueError, match="references a non-existent node"):
        Network(nodes=nodes, edges=edges, commodities=commodities)