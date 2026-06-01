from pydantic import BaseModel, Field, model_validator
from typing import Dict, List

class Node(BaseModel):
    id: str = Field(..., description="Unique name of physical location or ledger")
    capacity_limit: float = Field(float('inf'), ge=0)
    # Cost to hold one unit of a specific asset type per time step: {asset_type: cost}
    holding_costs: Dict[str, float] = Field(default_factory=dict)

class Edge(BaseModel):
    from_node: str
    to_node: str
    transit_time: int = Field(..., ge=1, description="Time steps required for transit")
    shared_capacity_limit: float = Field(float('inf'), ge=0)
    # Cost to move one unit of a specific asset type across this edge: {asset_type: cost}
    costs_per_unit: Dict[str, float] = Field(default_factory=dict)

class Commodity(BaseModel):
    id: str = Field(..., description="Unique identifier for this specific delivery request")
    asset_type: str = Field(..., description="The physical category of the asset (e.g., '20FT', 'USD')")
    origin: str = Field(..., description="The node where the asset starts")
    destination: str = Field(..., description="The node where the asset must arrive")
    volume: float = Field(..., gt=0, description="The quantity that must be moved")
    available_time: int = Field(..., ge=0, description="The time step when it becomes available at the origin")
    due_date: int = Field(..., ge=0, description="The time step when it must be at the destination")
    consumption_factor: float = Field(1.0, gt=0, description="Multiplier for shared edge capacity")

    @model_validator(mode='after')
    def validate_timeline(self):
        if self.due_date < self.available_time:
            raise ValueError(f"Commodity {self.id}: due_date cannot be earlier than available_time.")
        return self

class Network(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    commodities: List[Commodity]

    @model_validator(mode='after')
    def enforce_relational_integrity(self):
        valid_nodes = {n.id for n in self.nodes}
        
        for edge in self.edges:
            if edge.from_node not in valid_nodes or edge.to_node not in valid_nodes:
                raise ValueError(f"Edge {edge.from_node} -> {edge.to_node} references a non-existent node.")
                
        for comm in self.commodities:
            if comm.origin not in valid_nodes:
                raise ValueError(f"Commodity {comm.id} references an invalid origin: '{comm.origin}'.")
            if comm.destination not in valid_nodes:
                raise ValueError(f"Commodity {comm.id} references an invalid destination: '{comm.destination}'.")
        return self