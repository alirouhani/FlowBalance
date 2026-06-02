from abc import ABC, abstractmethod
from typing import Dict, Any
from flowbalance.core.entities import Network

class BaseSolver(ABC):
    """
    Abstract Base Class defining the contract for all mathematical optimization engines.
    """
    
    @abstractmethod
    def solve(self, network: Network, horizon: int) -> Dict[str, Any]:
        """
        Compiles the mathematical matrix, executes the solver, and extracts active flows.
        
        Args:
            network (Network): The validated Pydantic multi-commodity network.
            horizon (int): The number of discrete time steps.
            
        Returns:
            Dict[str, Any]: A dictionary containing 'status', 'objective_value', and 'flows'.
        """
        pass