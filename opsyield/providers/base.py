
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..core.models import NormalizedCost, Resource

class CloudProvider(ABC):
    @abstractmethod
    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        """Fetch cost data normalized to a common format"""
        pass

    @abstractmethod
    async def get_infrastructure(self) -> List[Resource]:
        """Discover infrastructure resources"""
        pass

    @abstractmethod
    def get_resource_metadata(self, resource_id: str) -> dict:
        pass

    async def get_utilization_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        """
        Fetch utilization metrics (CPU, Memory, IO) for the given resources.
        Returns the list of resources enriched with metrics.
        """
        return resources

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Check provider status (installed, authenticated)"""
        pass
