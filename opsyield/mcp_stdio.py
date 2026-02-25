import json
import os
import sys
from dataclasses import asdict
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

mcp = FastMCP("OpsYieldFinOps")
_orchestrator = Orchestrator()


@mcp.tool()
async def run_finops_intelligence(
    provider: str = "gcp",
    days: int = 7,
    project_id: str = "",
    subscription_id: str = ""
) -> str:
    """
    Run FinOps analysis for a given cloud provider.
    Falls back to GOOGLE_CLOUD_PROJECT if project_id not explicitly provided.
    """

    effective_project_id = project_id.strip() or os.getenv("GOOGLE_CLOUD_PROJECT")

    result = await _orchestrator.analyze(
        provider_name=provider,
        days=days,
        project_id=effective_project_id,
        subscription_id=subscription_id.strip() or None,
    )

    return json.dumps(adapt_analysis_result(result), default=str)


@mcp.tool()
async def aggregate_finops(
    providers: str = "gcp,aws",
    days: int = 7,
    subscription_id: str = ""
) -> str:
    """
    Aggregate analysis across multiple providers.
    """

    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    result = await _orchestrator.aggregate_analysis(
        providers=provider_list,
        days=days,
        subscription_id=subscription_id.strip() or None,
    )

    return json.dumps(adapt_analysis_result(result), default=str)


if __name__ == "__main__":
    # ⚠️ DO NOT add prints here
    # MCP handshake requires clean stdout
    mcp.run(transport="stdio")