"""
GCP Provider — Production-grade cloud status + cost analysis.

Status: subprocess.run(shell=True) for Windows .cmd compatibility.
Costs:  google-cloud-bigquery billing export with asyncio.to_thread().
Authentication is determined by CLI exit code, NOT by project list.
"""
import asyncio
import os
import shutil
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from ..core.models import NormalizedCost, Resource
from ..core.logging import get_logger
from .cli_utils import run_cli, parse_json

logger = get_logger(__name__)


# ——— Lazy BigQuery imports (optional dependency) ———
try:
    from google.cloud import bigquery
    from google.api_core import exceptions as gcp_exceptions
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False
    bigquery = None
    gcp_exceptions = None


class GCPProvider:
    """
    GCP cloud provider with status detection and BigQuery-based cost analysis.

    Cost retrieval requires:
      - Billing export to BigQuery enabled in GCP Console
      - IAM roles: BigQuery Data Viewer + BigQuery Job User
      - pip install google-cloud-bigquery
    """

    # BigQuery billing export dataset/table pattern
    _BQ_DATASET = "billing_export"
    _BQ_TABLE_PATTERN = "gcp_billing_export_v1_*"
    _BQ_RESOURCE_TABLE_PATTERN = "gcp_billing_export_resource_v1_*"

    def __init__(self, project_id: str = None, credentials_path: str = None):
        self.project_id = project_id
        self.credentials_path = credentials_path

    # -------------------------------------------------
    # Status Detection (unchanged from previous version)
    # -------------------------------------------------

    def get_status_sync(self) -> Dict[str, Any]:
        """
        Synchronous status check -- called via asyncio.to_thread().

        Authentication logic:
          1. shutil.which("gcloud") -> installed
          2. gcloud auth list --filter=status:ACTIVE --format=value(account)
             -> if exit code 0 AND stdout non-empty -> authenticated
          3. Fallback: gcloud auth application-default print-access-token
             -> if exit code 0 -> authenticated (service account / ADC)
          4. gcloud projects list --format=json (optional, for project data)
        """
        status: Dict[str, Any] = {
            "installed": False,
            "authenticated": False,
            "projects": [],
            "error": None,
            "debug": {},
        }

        # -- 1. Installation check --
        gcloud_path = shutil.which("gcloud")
        if not gcloud_path:
            status["error"] = "gcloud CLI not found on PATH"
            status["debug"]["which"] = None
            return status
        status["installed"] = True
        status["debug"]["which"] = gcloud_path

        # -- 2. Primary auth check --
        auth_cmd = "gcloud auth list --filter=status:ACTIVE --format=value(account)"
        auth = run_cli(auth_cmd, tag="GCP")
        status["debug"]["auth_list"] = {
            "stdout": auth["stdout"][:200],
            "stderr": auth["stderr"][:200],
            "returncode": auth["returncode"],
        }

        if auth["ok"] and auth["stdout"].strip():
            status["authenticated"] = True
            status["debug"]["active_account"] = auth["stdout"].strip().split("\n")[0]
        else:
            # -- 3. Fallback: Application Default Credentials --
            adc_cmd = "gcloud auth application-default print-access-token"
            adc = run_cli(adc_cmd, timeout=10, tag="GCP")
            status["debug"]["adc"] = {
                "returncode": adc["returncode"],
                "has_token": bool(adc["stdout"].strip()),
            }
            if adc["ok"] and adc["stdout"].strip():
                status["authenticated"] = True
                status["debug"]["auth_method"] = "application-default"
            else:
                status["error"] = auth["stderr"] or "No active gcloud account"

        # -- 4. Project list (informational, does NOT affect auth) --
        if status["authenticated"]:
            proj = run_cli("gcloud projects list --format=json", tag="GCP")
            status["debug"]["projects_list"] = {
                "returncode": proj["returncode"],
                "stdout_len": len(proj["stdout"]),
            }
            parsed = parse_json(proj["stdout"])
            if isinstance(parsed, list):
                status["projects"] = [
                    {"id": p.get("projectId", ""), "name": p.get("name", "")}
                    for p in parsed
                    if p.get("lifecycleState") == "ACTIVE"
                ]

        return status

    async def get_status(self) -> Dict[str, Any]:
        """Async wrapper -- runs blocking subprocess in a thread."""
        return await asyncio.to_thread(self.get_status_sync)

    # -------------------------------------------------
    # Cost Analysis via BigQuery Billing Export
    # -------------------------------------------------

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        from ..billing.gcp import GCPBillingProvider
        billing = GCPBillingProvider(project_id=self.project_id)
        return await billing.get_costs(days)



    # -------------------------------------------------
    # Resource-level costs (best-effort)
    # -------------------------------------------------

    def _build_resource_cost_query(self, project_id: str, days: int) -> str:
        """
        Build a BigQuery SQL query to estimate per-resource costs using the
        resource-level billing export table (if enabled).
        """
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        table = f"`{project_id}.{self._BQ_DATASET}.{self._BQ_RESOURCE_TABLE_PATTERN}`"

        # Note: schema differs across exports; this is best-effort and errors are handled.
        return f"""
            SELECT
                COALESCE(resource.name, resource.global_name, resource.id) AS resource_key,
                ANY_VALUE(service.description) AS service_name,
                ANY_VALUE(currency) AS currency,
                SUM(cost) AS total_cost
            FROM {table}
            WHERE
                DATE(usage_start_time) >= '{start_date}'
            GROUP BY
                resource_key
            ORDER BY
                total_cost DESC
            LIMIT 5000
        """

    def _get_resource_costs_sync(self, days: int) -> Dict[str, Dict[str, Any]]:
        """
        Return mapping: resource_key -> {cost_30d, currency, service}
        """
        if not HAS_BIGQUERY:
            return {}

        try:
            project_id = self._resolve_project_id()
        except Exception:
            return {}

        query = self._build_resource_cost_query(project_id, days)

        try:
            client = bigquery.Client(project=project_id)
            rows = list(client.query(query).result())
            out: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                key = row.get("resource_key")
                if not key:
                    continue
                raw_cost = row.get("total_cost", 0)
                cost_float = float(raw_cost) if isinstance(raw_cost, Decimal) else float(raw_cost or 0)
                out[str(key)] = {
                    "cost_30d": round(cost_float, 4),
                    "currency": row.get("currency", "USD"),
                    "service": row.get("service_name", "Unknown"),
                }
            return out
        except Exception as e:
            # Resource export might not be enabled; treat as optional.
            logger.info(f"[GCP Costs] Resource-cost query unavailable: {e}")
            return {}

    async def get_resource_costs(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Async wrapper for resource-level cost map (best-effort)."""
        return await asyncio.to_thread(self._get_resource_costs_sync, days)

    # -------------------------------------------------
    # Infrastructure (stub)
    # -------------------------------------------------

    async def get_infrastructure(self) -> List[Resource]:
        """
        Discovers infrastructure using modular collectors.
        """
        from ..collectors.gcp.compute import GCPComputeCollector
        from ..collectors.gcp.storage import GCPStorageCollector
        from ..collectors.gcp.sql import GCPSQLCollector

        collectors = [
            GCPComputeCollector(project_id=self.project_id),
            GCPStorageCollector(project_id=self.project_id),
            GCPSQLCollector(project_id=self.project_id)
        ]

        results = await asyncio.gather(*[c.collect() for c in collectors], return_exceptions=True)
        
        all_resources = []
        for res in results:
            if isinstance(res, list):
                all_resources.extend(res)
            else:
                logger.error(f"[GCP] Collector failed: {res}")
                
        return all_resources

    def get_resource_metadata(self, resource_id: str) -> dict:
        return {"id": resource_id, "provider": "gcp"}

    async def get_utilization_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        from ..collectors.gcp.metrics import GCPMetricsCollector
        collector = GCPMetricsCollector(project_id=self.project_id)
        return await collector.collect_metrics(resources, period_days)
