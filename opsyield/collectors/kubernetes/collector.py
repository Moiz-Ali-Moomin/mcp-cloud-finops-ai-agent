from typing import Dict, Any

from .opencost_client import OpenCostClient


class KubernetesCostCollector:
    def __init__(self, opencost_url: str = None):
        self.client = OpenCostClient(base_url=opencost_url)

    async def collect(self) -> Dict[str, Any]:
        """
        Fetch allocation data, aggregate cost by namespace, and return normalized cost structure.
        """
        allocation_data = await self.client.get_allocation()

        namespaces_cost: Dict[str, float] = {}

        # OpenCost /allocation typically returns data in a "data" list.
        # Example: {"data": [{"payments": {"name": "payments", "totalCost": 140.25}, ...}]}
        data = allocation_data.get("data", [])
        for window in data:
            if isinstance(window, dict):
                for namespace, details in window.items():
                    # Handle standard properties if needed, but typically it's namespace mapped to cost info
                    if isinstance(details, dict):
                        # Some OpenCost formats have "totalCost"
                        cost = details.get("totalCost", 0.0)

                        # Accumulate
                        if namespace not in namespaces_cost:
                            namespaces_cost[namespace] = 0.0
                        namespaces_cost[namespace] += float(cost)

        return {"provider": "kubernetes", "namespaces": namespaces_cost}
