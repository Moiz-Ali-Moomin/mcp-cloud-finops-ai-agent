"""
OpsYield API â€” No auth, no DB, no barriers.

Just start the server and fetch cloud data directly from GCP / AWS / Azure.
"""
import sys
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from ..core.orchestrator import Orchestrator
from ..core.logging import get_logger
from ..providers.factory import ProviderFactory
from .adapters.analysis_adapter import adapt_analysis_result

logger = get_logger(__name__)

# â”€â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = FastAPI(
    title="OpsYield API",
    version="0.2.0",
    description="Cloud FinOps API â€” fetch cost & resource data from GCP, AWS, Azure with zero auth overhead.",
)

# â”€â”€â”€ CORS â€” open for local/CLI usage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# â”€â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/health")
def health_check():
    """Quick liveness probe."""
    return {"status": "ok", "version": "0.2.0"}


@app.get("/api/cloud/status")
async def get_cloud_status():
    """
    Check which cloud CLIs are installed & authenticated (GCP / AWS / Azure).
    Runs concurrently â€” safe to call anytime.
    """
    try:
        return await ProviderFactory.get_all_statuses()
    except Exception as e:
        logger.error(f"Cloud status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analyze")
async def analyze(
    provider: str = Query(..., description="Cloud provider: gcp | aws | azure"),
    days: int = Query(30, description="Look-back window in days"),
    project_id: Optional[str] = Query(None, description="GCP project ID (optional)"),
    subscription_id: Optional[str] = Query(None, description="Azure subscription ID (optional)"),
):
    """
    Fetch cost + resource data for a single provider.

    Examples:
      GET /api/analyze?provider=gcp
      GET /api/analyze?provider=gcp&project_id=my-project&days=7
      GET /api/analyze?provider=aws&days=14
      GET /api/analyze?provider=azure&subscription_id=xxx
    """
    try:
        orchestrator = Orchestrator()
        result = await orchestrator.analyze(
            provider_name=provider,
            days=days,
            project_id=project_id,
            subscription_id=subscription_id,
        )
        return adapt_analysis_result(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/aggregate")
async def aggregate(
    providers: str = Query(..., description="Comma-separated providers, e.g. gcp,aws,azure"),
    days: int = Query(30, description="Look-back window in days"),
    subscription_id: Optional[str] = Query(None, description="Azure subscription ID (optional)"),
):
    """
    Fetch and merge cost + resource data across multiple providers.

    Example:
      GET /api/aggregate?providers=gcp,aws
      GET /api/aggregate?providers=gcp,aws,azure&days=7
    """
    try:
        provider_list = [p.strip() for p in providers.split(",") if p.strip()]
        if not provider_list:
            raise HTTPException(status_code=400, detail="No valid providers specified")
        orchestrator = Orchestrator()
        result = await orchestrator.aggregate_analysis(
            providers=provider_list,
            days=days,
            subscription_id=subscription_id,
        )
        return adapt_analysis_result(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """CLI entrypoint for the MCP API server."""
    uvicorn.run("opsyield.api.server:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
