import os
from typing import Any, Dict, List

from .base import CloudProvider
from ..collectors.kubernetes.collector import KubernetesCostCollector
from ..core.models import NormalizedCost, Resource


class KubernetesProvider(CloudProvider):
    name = "kubernetes"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        # Allows optional override from config dictionary, else fallback to environment via the collector's client defaults.
        opencost_url = self.config.get("opencost_url") or os.getenv("OPENCOST_URL")
        self.collector = KubernetesCostCollector(opencost_url=opencost_url)

    async def collect(self) -> Any:
        # Match the functionality requested in prompt for "async def collect(self)"
        return await self.collector.collect()

    # --- Implement CloudProvider Abstract Methods for factory compatibility ---

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        """
        Fetch cost data normalized to a common format.
        For now, this defers to the collector which returns a dictionary and translates it to NormalizedCost list.
        """
        raw_data = await self.collect()

        costs = []
        namespaces = raw_data.get("namespaces", {})

        # We dummy up a single day or total aggregation since OpenCost's /allocation
        # represents a time window (typically defaulting to recent window).
        # Normalizing to the structure typically returned.
        for ns, cost in namespaces.items():
            costs.append(
                NormalizedCost(
                    provider="kubernetes",
                    service="OpenCost",
                    region="global",  # Or cluster-specific if known
                    resource_id=f"namespace/{ns}",
                    cost=round(cost, 4),
                    currency="USD",
                    timestamp=None,  # Depending on data returned
                    tags={"namespace": ns},
                )
            )
        return costs

    async def get_infrastructure(self) -> List[Resource]:
        """Discover infrastructure resources"""
        # Retrieve assets from OpenCost or equivalent in the future
        return []

    def get_resource_metadata(self, resource_id: str) -> dict:
        return {"id": resource_id, "provider": "kubernetes"}

    async def get_status(self) -> Dict[str, Any]:
        """Check provider status (installed, authenticated)"""
        # For OpenCost, being \"authenticated/running\" is effectively whether we can ping the URL.
        # This will be used by the async Factory logic.
        status: Dict[str, Any] = {
            "installed": True,
            "authenticated": False,
            "error": None,
            "debug": {},
        }

        try:
            # We just test the collector. If it fetches any allocation data successfully, it's 'active'.
            await self.collect()
            status["authenticated"] = True
        except Exception as e:
            status["error"] = str(e)
            status["debug"]["exception"] = str(e)

        return status
