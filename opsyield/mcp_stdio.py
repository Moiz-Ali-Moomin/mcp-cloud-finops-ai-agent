import json
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'opsyield' package is discoverable
# Required when Claude Desktop (or other MCP clients) run this script directly
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Force ALL logs to stderr (never stdout) — critical for MCP protocol
from opsyield.core.logging import configure_logging
configure_logging(level="ERROR", stream=sys.stderr)

from mcp.server.fastmcp import FastMCP
from opsyield.core.orchestrator import Orchestrator
from opsyield.api.adapters.analysis_adapter import adapt_analysis_result
from opsyield.core.context import set_project, get_project

mcp = FastMCP("OpsYieldFinOps")
_orchestrator = Orchestrator()


def _resolve(project_id: str) -> str:
    return project_id.strip() or get_project() or os.getenv("GOOGLE_CLOUD_PROJECT") or ""


@mcp.tool()
async def configure_project(project_id: str) -> str:
    """
    Set the active GCP project ID for all subsequent FinOps calls.
    Call this first whenever the user mentions a GCP project ID.
    Example: configure_project(project_id="ecommerce-microservice-53")
    """
    set_project(project_id.strip())
    return f"Active GCP project set to: {project_id.strip()}"


@mcp.tool()
async def get_billing_costs(
    provider: str = "gcp",
    days: int = 30,
    project_id: str = "",
    subscription_id: str = ""
) -> str:
    """
    STEP 1 — Fast billing costs only (~5-8s). Call this first to show cost data immediately.
    Returns: total_cost, cost_drivers, daily_trends.
    Follow up with get_infrastructure() for resource details.
    Note: GCP billing has a ~10 day lag, days>=14 recommended.
    """
    from opsyield.providers.factory import ProviderFactory
    from opsyield.api.adapters.analysis_adapter import adapt_analysis_result
    from opsyield.core.models import AnalysisResult
    from datetime import datetime

    pid = _resolve(project_id)
    sid = subscription_id.strip() or None

    provider_obj = ProviderFactory.get_provider(provider, project_id=pid, subscription_id=sid)
    costs = await provider_obj.get_costs(days)

    daily_map: dict = {}
    total_cost = 0.0
    cost_by_service: dict = {}
    for c in costs:
        day = c.timestamp.strftime("%Y-%m-%d") if hasattr(c.timestamp, "strftime") else str(c.timestamp)[:10]
        daily_map[day] = daily_map.get(day, 0.0) + c.cost
        total_cost += c.cost
        cost_by_service[c.service] = cost_by_service.get(c.service, 0.0) + c.cost

    daily_trends = [{"date": d, "amount": round(v, 4)} for d, v in sorted(daily_map.items())]
    cost_drivers = sorted(
        [{"service": s, "cost": round(a, 4)} for s, a in cost_by_service.items()],
        key=lambda x: x["cost"], reverse=True
    )[:10]

    result = {
        "meta": {"provider": provider, "period_days": str(days), "generated_at": datetime.utcnow().isoformat()},
        "summary": {"total_cost": round(total_cost, 4), "currency": costs[0].currency if costs else "USD"},
        "cost_drivers": cost_drivers,
        "daily_trends": daily_trends,
    }
    return json.dumps(result, default=str)


@mcp.tool()
async def get_infrastructure(
    provider: str = "gcp",
    project_id: str = "",
    subscription_id: str = ""
) -> str:
    """
    STEP 2 — Infrastructure resources (~5-10s). Call after get_billing_costs().
    Returns: resource list, resource_types breakdown, running count.
    """
    from opsyield.providers.factory import ProviderFactory
    from datetime import datetime

    pid = _resolve(project_id)
    sid = subscription_id.strip() or None

    provider_obj = ProviderFactory.get_provider(provider, project_id=pid, subscription_id=sid)
    resources = await provider_obj.get_infrastructure()

    resource_types: dict = {}
    running_count = 0
    resource_list = []
    for r in resources:
        from opsyield.core.models import Resource
        if isinstance(r, Resource):
            rtype = r.type or "unknown"
            resource_types[rtype] = resource_types.get(rtype, 0) + 1
            if r.state and r.state.upper() in ("RUNNING", "ACTIVE", "ONLINE"):
                running_count += 1
            resource_list.append({"id": r.id, "name": r.name, "type": r.type, "state": r.state})

    result = {
        "meta": {"provider": provider, "generated_at": datetime.utcnow().isoformat()},
        "summary": {"resource_count": len(resources), "running_count": running_count},
        "resource_types": resource_types,
        "resources": resource_list[:50],
    }
    return json.dumps(result, default=str)


@mcp.tool()
async def run_finops_intelligence(
    provider: str = "gcp",
    days: int = 30,
    project_id: str = "",
    subscription_id: str = ""
) -> str:
    """
    Full FinOps analysis (billing + infrastructure combined). Use this for a complete report.
    For faster display, call get_billing_costs() then get_infrastructure() separately instead.
    Note: GCP billing export has a ~10 day lag, days>=14 recommended.
    """
    pid = _resolve(project_id)

    result = await _orchestrator.analyze(
        provider_name=provider,
        days=days,
        project_id=pid,
        subscription_id=subscription_id.strip() or None,
    )

    return json.dumps(adapt_analysis_result(result), default=str)


@mcp.tool()
async def aggregate_finops(
    providers: str = "gcp,aws",
    days: int = 30,
    project_id: str = "",
    subscription_id: str = ""
) -> str:
    """
    Aggregate FinOps analysis across multiple cloud providers.
    project_id priority: explicit arg → context (set via configure_project) → GOOGLE_CLOUD_PROJECT env var.
    """
    pid = _resolve(project_id)

    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    result = await _orchestrator.aggregate_analysis(
        providers=provider_list,
        days=days,
        project_id=pid,
        subscription_id=subscription_id.strip() or None,
    )

    return json.dumps(adapt_analysis_result(result), default=str)


if __name__ == "__main__":
    # ⚠️ DO NOT add prints here
    # MCP handshake requires clean stdout
    mcp.run(transport="stdio")