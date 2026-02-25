from typing import List
from datetime import datetime, timedelta
import boto3
from .base import BillingProvider
from ..core.models import NormalizedCost
from ..core.logging import get_logger

logger = get_logger(__name__)

class AWSBillingProvider(BillingProvider):
    def __init__(self, use_cur: bool = False, region: str = "us-east-1"):
        self.use_cur = use_cur
        self.region = region

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        import asyncio
        if self.use_cur:
             # CUR via Athena implementation would go here
             # Requires: Athena Client, Database, Table, S3 output location
             logger.warning("AWS CUR implementation pending configuration. Falling back to Cost Explorer.")
        
        return await asyncio.to_thread(self._get_ce_costs, days)

    def _get_ce_costs(self, days: int) -> List[NormalizedCost]:
        costs = []
        try:
            session = boto3.Session(region_name=self.region)
            ce = session.client("ce")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            response = ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            for rbt in response.get("ResultsByTime", []):
                dt = datetime.strptime(rbt["TimePeriod"]["Start"], "%Y-%m-%d")
                for group in rbt.get("Groups", []):
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if amount > 0.001:
                        costs.append(NormalizedCost(
                            provider="aws",
                            service=group["Keys"][0],
                            region=self.region,
                            resource_id="aggregated",
                            cost=round(amount, 4),
                            currency="USD",
                            timestamp=dt,
                            tags={},
                        ))
        except Exception as e:
            logger.error(f"AWS Cost Explorer failed: {e}")
        return costs
