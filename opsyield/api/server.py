"""
OpsYield API
Defines FastAPI application and routes.
"""

from typing import Optional, List
from enum import Enum

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..core.orchestrator import Orchestrator
from ..core.logging import get_logger
from ..providers.factory import ProviderFactory
from .adapters.analysis_adapter import adapt_analysis_result


logger = get_logger(__name__)
_orchestrator = Orchestrator()


# ─────────────────────────────────────────────
# Provider Enum (Validation Layer)
# ─────────────────────────────────────────────

class Provider(str, Enum):
    gcp = "gcp"
    aws = "aws"
    azure = "azure"


# ─────────────────────────────────────────────
# App Definition
# ─────────────────────────────────────────────

app = FastAPI(
    title="OpsYield API",
    version="0.2.0",
    description="Internal multi-cloud FinOps API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # internal tool
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/api/cloud/status")
async def get_cloud_status():
    try:
        return await ProviderFactory.get_all_statuses()
    except Exception as e:
        logger.error(f"Cloud status check failed: {e}")
        raise HTTPException(status_code=500, detail="Cloud status check failed")


@app.get("/api/analyze")
async def analyze(
    provider: Provider = Query(...),
    days: int = Query(30, ge=1, le=365),
    project_id: Optional[str] = Query(None),
    subscription_id: Optional[str] = Query(None),
):
    try:
        result = await _orchestrator.analyze(
            provider_name=provider.value,
            days=days,
            project_id=project_id,
            subscription_id=subscription_id,
        )
        return adapt_analysis_result(result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Analysis failed for {provider.value}: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@app.get("/api/aggregate")
async def aggregate(
    providers: List[Provider] = Query(...),
    days: int = Query(30, ge=1, le=365),
    subscription_id: Optional[str] = Query(None),
):
    try:
        provider_list = [p.value for p in providers]
        result = await _orchestrator.aggregate_analysis(
            providers=provider_list,
            days=days,
            subscription_id=subscription_id,
        )

        return adapt_analysis_result(result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        raise HTTPException(status_code=500, detail="Aggregation failed")