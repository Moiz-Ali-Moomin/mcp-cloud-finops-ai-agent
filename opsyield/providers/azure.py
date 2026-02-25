"""
Azure Provider — Production-grade cloud status detection.

Uses subprocess.run(shell=True) for Windows .cmd compatibility.
Authentication is determined by CLI exit code of `az account show`.
"""
import os
import shutil
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..core.models import NormalizedCost, Resource
from ..core.logging import get_logger
from .cli_utils import run_cli, parse_json

logger = get_logger(__name__)


class AzureProvider:
    def __init__(self, subscription_id: str = None):
        self.subscription_id = subscription_id

    def get_status_sync(self) -> Dict[str, Any]:
        """
        Synchronous status check -- called via asyncio.to_thread().

        Authentication logic:
          1. shutil.which("az") -> installed
          2. az account show --output json
             -> exit code 0 -> authenticated
             -> Parse id (subscription), name, user from JSON stdout
        """
        status: Dict[str, Any] = {
            "installed": False,
            "authenticated": False,
            "subscriptions": [],
            "error": None,
            "debug": {},
        }

        # -- 1. Installation check --
        az_path = shutil.which("az")
        if not az_path:
            status["error"] = "Azure CLI not found on PATH"
            status["debug"]["which"] = None
            return status
        status["installed"] = True
        status["debug"]["which"] = az_path

        # -- 2. Authentication check via az account show --
        show_cmd = "az account show --output json"
        show = run_cli(show_cmd, tag="AZ")
        status["debug"]["account_show"] = {
            "stdout": show["stdout"][:400],
            "stderr": show["stderr"][:300],
            "returncode": show["returncode"],
        }

        if show["ok"]:
            # CLI exit code 0 -> authenticated
            status["authenticated"] = True
            parsed = parse_json(show["stdout"])
            if isinstance(parsed, dict):
                sub_id = parsed.get("id", "")
                sub_name = parsed.get("name", "")
                user_info = parsed.get("user", {})

                if sub_id:
                    status["subscriptions"] = [{"id": sub_id, "name": sub_name}]
                    if not self.subscription_id:
                        self.subscription_id = sub_id

                status["debug"]["user"] = user_info.get("name", "")
                status["debug"]["tenant"] = parsed.get("tenantId", "")
        else:
            # Fallback: try az account list
            list_cmd = "az account list --output json"
            acct_list = run_cli(list_cmd, tag="AZ")
            status["debug"]["account_list"] = {
                "returncode": acct_list["returncode"],
                "stdout_len": len(acct_list["stdout"]),
            }

            if acct_list["ok"]:
                parsed_list = parse_json(acct_list["stdout"])
                if isinstance(parsed_list, list) and len(parsed_list) > 0:
                    status["authenticated"] = True
                    status["subscriptions"] = [
                        {"id": a.get("id", ""), "name": a.get("name", "")}
                        for a in parsed_list
                        if isinstance(a, dict) and a.get("state") == "Enabled"
                    ]
                    if status["subscriptions"] and not self.subscription_id:
                        self.subscription_id = status["subscriptions"][0]["id"]
                else:
                    status["error"] = "No Azure subscriptions. Run: az login"
            else:
                status["error"] = show["stderr"] or "Azure credentials not configured"

        # -- 3. Environment hints --
        status["debug"]["env"] = {
            "AZURE_CONFIG_DIR": os.environ.get("AZURE_CONFIG_DIR", "(not set)"),
        }

        return status

    async def get_status(self) -> Dict[str, Any]:
        """Async wrapper -- runs blocking subprocess in a thread."""
        import asyncio
        return await asyncio.to_thread(self.get_status_sync)

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        from ..billing.azure import AzureBillingProvider
        billing = AzureBillingProvider(subscription_id=self.subscription_id)
        return await billing.get_costs(days)

    async def get_infrastructure(self) -> List[Resource]:
        """
        Discovers infrastructure using modular collectors.
        """
        from ..collectors.azure.compute import AzureComputeCollector
        from ..collectors.azure.storage import AzureStorageCollector
        from ..collectors.azure.sql import AzureSQLCollector

        collectors = [
            AzureComputeCollector(subscription_id=self.subscription_id),
            AzureStorageCollector(subscription_id=self.subscription_id),
            AzureSQLCollector(subscription_id=self.subscription_id)
        ]

        import asyncio
        results = await asyncio.gather(*[c.collect() for c in collectors], return_exceptions=True)
        
        all_resources = []
        for res in results:
            if isinstance(res, list):
                all_resources.extend(res)
            else:
                logger.error(f"[Azure] Collector failed: {res}")
                
        return all_resources

    def get_resource_metadata(self, resource_id: str) -> dict:
        return {"id": resource_id, "provider": "azure"}

    async def get_utilization_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        from ..collectors.azure.metrics import AzureMetricsCollector
        collector = AzureMetricsCollector(subscription_id=self.subscription_id)
        return await collector.collect_metrics(resources, period_days)
