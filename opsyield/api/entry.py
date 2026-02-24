"""
OpsYield MCP Server â€” Clean Multi-Cloud Build
Version: 1.3.0

Supports:
- GCP (Service Account JSON)
- AWS (boto3)
- Azure (Service Principal)

No CLI dependency for cost.
Stable async execution.
"""

import os
import sys
import asyncio
import logging
import time
import threading
from datetime import datetime, timedelta, timezone
from mcp.server.fastmcp import FastMCP

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Setup
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

VERSION = "1.3.0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-finops")

mcp = FastMCP("OpsYieldFinOps")

_GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
_ADC_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Thread-Safe Token Cache (GCP)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TokenCache:
    def __init__(self):
        self._token = None
        self._expiry = 0
        self._lock = threading.Lock()

    def get_valid_token(self):
        with self._lock:
            if self._token and time.time() < self._expiry:
                return self._token
        return None

    def set_token(self, token, ttl=3000):
        with self._lock:
            self._token = token
            self._expiry = time.time() + ttl

_GCP_CACHE = TokenCache()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GCP AUTH
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_gcp_token():
    token = _GCP_CACHE.get_valid_token()
    if token:
        return token

    if not _ADC_PATH:
        return "Error: GOOGLE_APPLICATION_CREDENTIALS not set."

    if not os.path.exists(_ADC_PATH):
        return f"Error: Credential file not found at {_ADC_PATH}"

    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests

        creds = service_account.Credentials.from_service_account_file(
            _ADC_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        _GCP_CACHE.set_token(creds.token)
        return creds.token

    except Exception as e:
        return f"Error: GCP Authentication failed â€” {e}"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GCP COST
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _gcp_costs_impl(project_id: str, days: int) -> str:

    def _sync():
        token = _get_gcp_token()
        if token.startswith("Error"):
            return token

        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        sql = f"""
        SELECT service.description AS service,
               currency,
               ROUND(SUM(cost), 2) AS total
        FROM `{project_id}.billing_export.gcp_billing_export_v1_*`
        WHERE _PARTITIONTIME >= TIMESTAMP('{start}')
          AND cost > 0
        GROUP BY service, currency
        ORDER BY total DESC
        LIMIT 10
        """

        try:
            import httpx

            url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"query": sql, "useLegacySql": False}

            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                return f"GCP Error {resp.status_code}: {resp.text[:200]}"

            data = resp.json()
            rows = data.get("rows", [])

            if not rows:
                return f"GCP: No cost data for last {days} days."

            total = sum(float(r['f'][2]['v']) for r in rows)
            currency = rows[0]['f'][1]['v']

            lines = [
                f"GCP FinOps â€” {project_id} ({days} days)",
                f"Total: {currency} {total:,.2f}",
                "Services:"
            ]

            for r in rows[:8]:
                lines.append(f"â€¢ {r['f'][0]['v']}: {currency} {float(r['f'][2]['v']):,.2f}")

            return "\n".join(lines)

        except Exception as e:
            return f"GCP REST Error: {e}"

    return await asyncio.to_thread(_sync)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# AWS COST
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _aws_costs_impl(days: int) -> str:

    def _sync():
        try:
            import boto3

            ce = boto3.client("ce", region_name="us-east-1")

            end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
            )

            totals = {}
            for day in resp["ResultsByTime"]:
                for group in day["Groups"]:
                    svc = group["Keys"][0]
                    amt = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    totals[svc] = totals.get(svc, 0) + amt

            if not totals:
                return f"AWS: No substantial costs for {days} days."

            grand = sum(totals.values())

            lines = [
                f"AWS FinOps ({days} days)",
                f"Total: USD {grand:,.2f}",
                "Services:"
            ]

            for svc, amt in sorted(totals.items(), key=lambda x: -x[1])[:8]:
                lines.append(f"â€¢ {svc}: USD {amt:,.2f}")

            return "\n".join(lines)

        except Exception as e:
            return f"AWS Error: {e}"

    return await asyncio.to_thread(_sync)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# AZURE COST
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _azure_costs_impl(days: int) -> str:

    def _sync():
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.costmanagement import CostManagementClient

            subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
            client_id = os.environ.get("AZURE_CLIENT_ID")
            client_secret = os.environ.get("AZURE_CLIENT_SECRET")
            tenant_id = os.environ.get("AZURE_TENANT_ID")

            if not all([subscription_id, client_id, client_secret, tenant_id]):
                return "Azure Error: Missing Azure credentials."

            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )

            client = CostManagementClient(credential)

            end = datetime.utcnow()
            start = end - timedelta(days=days)

            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start.isoformat(),
                    "to": end.isoformat()
                },
                "dataset": {
                    "granularity": "None",
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        }
                    }
                }
            }

            scope = f"/subscriptions/{subscription_id}"
            result = client.query.usage(scope=scope, parameters=query)

            total = 0
            for row in result.rows:
                total += float(row[1])

            return f"Azure FinOps ({days} days)\nTotal: ${total:,.2f}"

        except Exception as e:
            return f"Azure Error: {e}"

    return await asyncio.to_thread(_sync)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN TOOL
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mcp.tool()
async def run_finops_intelligence(provider: str = "gcp", days: int = 7, project_id: str = "") -> str:
    p = provider.lower().strip()

    if p == "gcp":
        return await asyncio.wait_for(
            _gcp_costs_impl(project_id or _GCP_PROJECT, days),
            timeout=60
        )

    elif p == "aws":
        return await asyncio.wait_for(
            _aws_costs_impl(days),
            timeout=30
        )

    elif p == "azure":
        return await asyncio.wait_for(
            _azure_costs_impl(days),
            timeout=30
        )

    else:
        return f"Provider '{provider}' not supported."

@mcp.tool()
async def debug_env() -> str:
    return f"""
GCP_PROJECT = {_GCP_PROJECT}
AZURE_SUBSCRIPTION_ID = {os.environ.get("AZURE_SUBSCRIPTION_ID")}
"""

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    logger.info(f"--- OpsYield MCP Server v{VERSION} Starting ---")
    mcp.run(transport="stdio")