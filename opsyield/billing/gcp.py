from typing import List
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import concurrent.futures
from .base import BillingProvider
from ..core.models import NormalizedCost
from ..core.logging import get_logger
import os

logger = get_logger(__name__)


def _load_credentials():
    """
    Load GCP credentials, bypassing the GCE metadata server probe that can
    hang for 30-60s in non-GCE environments (e.g. the MCP stdio server).

    Priority:
      1. GOOGLE_APPLICATION_CREDENTIALS env var (service account JSON)
      2. ADC file (~/.config/gcloud/application_default_credentials.json)
      3. Fallback to google.auth.default() with GCE disabled
    """
    import json
    from google.auth.transport.requests import Request as GoogleAuthRequest

    # 1. Service account key file
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and os.path.exists(sa_path):
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return creds

    # 2. ADC authorized_user file (gcloud auth application-default login)
    adc_paths = [
        os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
        os.path.join(os.environ.get("APPDATA", ""), "gcloud", "application_default_credentials.json"),
    ]
    for adc_path in adc_paths:
        if os.path.exists(adc_path):
            try:
                with open(adc_path) as f:
                    info = json.load(f)
                if info.get("type") == "authorized_user":
                    from google.oauth2.credentials import Credentials
                    creds = Credentials(
                        token=None,
                        refresh_token=info["refresh_token"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=info["client_id"],
                        client_secret=info["client_secret"],
                    )
                    if not creds.valid:
                        creds.refresh(GoogleAuthRequest())
                    return creds
            except Exception as e:
                logger.warning(f"Failed to load ADC from {adc_path}: {e}")

    # 3. Fallback — disable GCE metadata probe via env var
    os.environ.setdefault("NO_GCE_CHECK", "true")
    import google.auth
    creds, _ = google.auth.default()
    if not creds.valid:
        creds.refresh(GoogleAuthRequest())
    return creds


# Shared executor — limits BQ threads and allows daemon shutdown
_BQ_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="bq")

# Hard wall-clock budget for the entire BQ call (submit + wait for results).
# MCP server environment can be slow on first BQ slot allocation (~20-25s cold).
_BQ_TIMEOUT_S = 55


class GCPBillingProvider(BillingProvider):
    _BQ_DATASET = "billing_export"
    _BQ_TABLE_PATTERN = "gcp_billing_export_v1_*"

    def __init__(self, project_id: str = None):
        from ..core.context import get_project
        self.project_id = (
            project_id
            or get_project()
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        loop = asyncio.get_running_loop()
        try:
            # Run in dedicated executor so cancellation doesn't orphan the thread pool
            return await asyncio.wait_for(
                loop.run_in_executor(_BQ_EXECUTOR, self._get_costs_sync, days),
                timeout=_BQ_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.error(f"GCP Billing query timed out after {_BQ_TIMEOUT_S}s")
            return []
        except asyncio.CancelledError:
            # MCP cancelled the request — log and propagate so the session cleans up
            logger.warning("GCP Billing query cancelled by MCP client")
            raise

    def _get_costs_sync(self, days: int) -> List[NormalizedCost]:
        try:
            from google.cloud import bigquery
        except ImportError:
            logger.error("google-cloud-bigquery not installed")
            return []

        if not self.project_id:
            logger.error("No project_id for GCP billing")
            return []

        # GCP billing export has a ~10 day lag — enforce a minimum 14-day window
        effective_days = max(days, 14)
        start_date = (datetime.utcnow() - timedelta(days=effective_days)).strftime("%Y-%m-%d")
        table = f"`{self.project_id}.{self._BQ_DATASET}.{self._BQ_TABLE_PATTERN}`"

        # _TABLE_SUFFIX only works on date-sharded tables (suffix = YYYYMMDD).
        # Billing exports use billing-account-ID suffixes, so filter by usage_start_time only.
        query = f"""
            SELECT
                service.description    AS service_name,
                currency               AS currency,
                SUM(cost)              AS total_cost,
                MIN(usage_start_time)  AS usage_timestamp
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
            creds = _load_credentials()
            client = bigquery.Client(project=self.project_id, credentials=creds)
            job_config = bigquery.QueryJobConfig(use_query_cache=True)
            query_job = client.query(query, job_config=job_config)
            # Use a shorter timeout here — asyncio.wait_for above is the real guard
            rows = list(query_job.result(timeout=50))

            costs = []
            now = datetime.utcnow()
            for row in rows:
                raw_cost = row.get("total_cost", 0)
                cost_float = float(raw_cost) if isinstance(raw_cost, Decimal) else float(raw_cost or 0)
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
