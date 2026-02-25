# mcp_sse.py

import json
import os
import sys
from pathlib import Path

# Ensure project root is discoverable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from opsyield.core.logging import configure_logging
configure_logging(level="ERROR", stream=sys.stderr)

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from opsyield.core.orchestrator import Orchestrator
from opsyield.api.adapters.analysis_adapter import adapt_analysis_result


# Disable DNS rebinding protection for tunnel-based deployments (ngrok, Cloudflare)
# Field name is 'enable_dns_rebinding_protection', NOT 'enabled'
mcp = FastMCP(
    "OpsYieldFinOps",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

_orchestrator = Orchestrator()


@mcp.tool()
async def run_finops_intelligence(
    provider: str = "gcp",
    days: int = 7,
    project_id: str = "",
    subscription_id: str = ""
) -> str:

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

    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    result = await _orchestrator.aggregate_analysis(
        providers=provider_list,
        days=days,
        subscription_id=subscription_id.strip() or None,
    )

    return json.dumps(adapt_analysis_result(result), default=str)


if __name__ == "__main__":
    import uvicorn

    app = mcp.sse_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )