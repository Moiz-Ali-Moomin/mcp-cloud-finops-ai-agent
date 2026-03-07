import os
import httpx
from typing import Dict, Any


class OpenCostClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("OPENCOST_URL", "http://localhost:9003")

    async def get_allocation(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/allocation")
            response.raise_for_status()
            return response.json()

    async def get_assets(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/assets")
            response.raise_for_status()
            return response.json()
