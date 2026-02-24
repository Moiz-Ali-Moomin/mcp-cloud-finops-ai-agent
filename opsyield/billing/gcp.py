from typing import List
from datetime import datetime, timedelta
import time
from decimal import Decimal
import asyncio
from .base import BillingProvider
from ..core.models import NormalizedCost
from ..core.logging import get_logger
import os

logger = get_logger(__name__)

class GCPBillingProvider(BillingProvider):
    # BigQuery billing export dataset/table pattern
    _BQ_DATASET = "billing_export"
    _BQ_TABLE_PATTERN = "gcp_billing_export_v1_*"

    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        return await asyncio.to_thread(self._get_costs_sync, days)

    def _get_costs_sync(self, days: int) -> List[NormalizedCost]:
        try:
            from google.cloud import bigquery
        except ImportError:
            logger.error("google-cloud-bigquery not installed")
            return []

        if not self.project_id:
            logger.error("No project_id for GCP billing")
            return []

        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        table = f"`{self.project_id}.{self._BQ_DATASET}.{self._BQ_TABLE_PATTERN}`"
        
        query = f"""
            SELECT
                service.description    AS service_name,
                currency               AS currency,
                SUM(cost)              AS total_cost,
                min(usage_start_time)  AS usage_timestamp
            FROM {table}
            WHERE
                DATE(usage_start_time) >= '{start_date}'
                AND cost > 0
            GROUP BY
                service_name, currency
            ORDER BY
                total_cost DESC
        """

        try:
            client = bigquery.Client(project=self.project_id)
            query_job = client.query(query)
            rows = list(query_job.result())
            
            costs = []
            now = datetime.utcnow() # Use query timestamp if available
            
            for row in rows:
                raw_cost = row.get("total_cost", 0)
                cost_float = float(raw_cost) if isinstance(raw_cost, Decimal) else float(raw_cost or 0)
                
                # BigQuery returns datetime objects
                ts = row.get("usage_timestamp") or now

                costs.append(NormalizedCost(
                    provider="gcp",
                    service=row.get("service_name", "Unknown"),
                    region="global",
                    resource_id="aggregated",
                    cost=round(cost_float, 4),
                    currency=row.get("currency", "USD"),
                    timestamp=ts,
                    tags={},
                    project_id=self.project_id
                ))
            return costs

        except Exception as e:
            logger.error(f"GCP Billing query failed: {e}")
            return []
