from typing import List
from datetime import datetime, timedelta
import asyncio
from .base import BillingProvider
from ..core.models import NormalizedCost
from ..core.logging import get_logger
from azure.identity import DefaultAzureCredential
import os

logger = get_logger(__name__)

class AzureBillingProvider(BillingProvider):
    def __init__(self, subscription_id: str = None):
        self.credential = DefaultAzureCredential()
        self.subscription_id = subscription_id or os.environ.get("AZURE_SUBSCRIPTION_ID")

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        return await asyncio.to_thread(self._get_costs_sync, days)

    def _get_costs_sync(self, days: int) -> List[NormalizedCost]:
        costs = []
        try:
            # Requires azure-mgmt-costmanagement
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import QueryDefinition, QueryTimePeriod, QueryDataset, QueryAggregation, QueryGrouping

            if not self.subscription_id:
                raise ValueError("AZURE_SUBSCRIPTION_ID is not set")

            client = CostManagementClient(self.credential)
            scope = f"/subscriptions/{self.subscription_id}"
            
            end = datetime.now()
            start = end - timedelta(days=days)
            
            # Query definition
            # Group by ServiceName
            query = QueryDefinition(
                type="Usage",
                timeframe="Custom",
                time_period=QueryTimePeriod(from_property=start, to=end),
                dataset=QueryDataset(
                    granularity="Daily",
                    aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    grouping=[QueryGrouping(type="Dimension", name="ServiceName")]
                )
            )

            result = client.query.usage(scope, query)
            
            # Parse result
            # Columns: [Cost, UsageDate, ServiceName, Currency] usually
            # But depends on query structure. 
            # SDK returns a custom object with columns and rows.
            
            columns = {c.name: i for i, c in enumerate(result.columns)}
            cost_idx = columns.get("totalCost")
            date_idx = columns.get("UsageDate")
            service_idx = columns.get("ServiceName")
            currency_idx = columns.get("Currency")
            
            for row in result.rows:
                amount = row[cost_idx]
                dt_val = row[date_idx] # int or str YYYYMMDD? usually specific format
                service_name = row[service_idx]
                currency = row[currency_idx] if currency_idx is not None else "USD"

                if isinstance(dt_val, int): 
                    # 20230101
                    ts = datetime.strptime(str(dt_val), "%Y%m%d")
                elif isinstance(dt_val, str):
                    ts = datetime.fromisoformat(dt_val)
                else:
                    ts = datetime.now()

                costs.append(NormalizedCost(
                    provider="azure",
                    service=service_name,
                    region="global",
                    resource_id="aggregated",
                    cost=float(amount),
                    currency=currency,
                    timestamp=ts,
                    subscription_id=self.subscription_id
                ))

        except ImportError:
            logger.warning("azure-mgmt-costmanagement not installed")
        except Exception as e:
            logger.error(f"Azure Cost Management failed: {e}")
        
        return costs
