from ..base import BaseCollector
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from typing import Optional
import os

class AzureBaseCollector(BaseCollector):
    def __init__(self, subscription_id: Optional[str] = None, region: str = "global"):
        super().__init__("azure", region)
        self.credential = DefaultAzureCredential()
        self.subscription_id = subscription_id or os.environ.get("AZURE_SUBSCRIPTION_ID")
        
    def _get_subscription_id(self) -> str:
        if self.subscription_id:
            return self.subscription_id
        # Fallback: try to finding first subscription
        # This is async in nature if we want to be truly async, but 
        # DefaultAzureCredential sync usage is common for init.
        # We will assume env var or explicit pass for now to avoid SDK complexity in init.
        raise ValueError("AZURE_SUBSCRIPTION_ID is not set.")

    async def _handle_azure_error(self, operation: str, error: Exception):
        self._handle_error(operation, error)
