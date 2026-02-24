from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from ..core.models import NormalizedCost

class BillingProvider(ABC):
    @abstractmethod
    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        """
        Fetch cost data normalized to the unified schema.
        """
        pass
