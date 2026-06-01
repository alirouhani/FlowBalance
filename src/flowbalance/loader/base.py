from abc import ABC, abstractmethod
from flowbalance.core.entities import Network

class BaseLoader(ABC):
    """Abstract Base Class defining the contract for all network data ingestion."""
    
    @abstractmethod
    def load_network(self) -> Network:
        """Parses raw input sources and returns a fully validated Network container."""
        pass