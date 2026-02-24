from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from .models import NormalizedCost

class BaseProvider(ABC):
    """
    Abstract base class for all cloud providers.
    Enforces strict interface implementation.
    """
    
    @abstractmethod
    def get_costs(self, start_date: datetime, end_date: datetime) -> List[NormalizedCost]:
        """
        Retrieve cost data from the provider and return as NormalizedCost objects.
        """
        pass

    @abstractmethod
    def get_resource_metadata(self, resource_id: str) -> dict:
        """
        Retrieve detailed metadata for a specific resource.
        """
        pass

class OptimizationStrategy(ABC):
    """
    Interface for optimization strategies.
    """
    
    @abstractmethod
    def analyze(self, cost_item: NormalizedCost) -> Optional[dict]:
        """
        Analyze a NormalizedCost item and return optimization suggestions if any.
        """
        pass
