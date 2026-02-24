"""
Orchestrator — No-auth, no-DB provider dispatcher.

Calls cloud providers directly (GCP, AWS, Azure) via CLI/SDK.
No authentication middleware, no database, no Redis.

Aggregation logic is delegated to AggregationEngine (SRP).
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..providers.factory import ProviderFactory
from .models import AnalysisResult, Resource
from .aggregation import AggregationEngine
from .logging import get_logger, TimedOperation

logger = get_logger(__name__)


class Orchestrator:
    """
    Dispatches analysis requests directly to cloud providers.
    No session, no org_id, no DB — pure provider calls.

    Aggregation is delegated to AggregationEngine.
    """

    def __init__(self):
        self._aggregator = AggregationEngine()

    async def analyze(
        self,
        provider_name: str,
        days: int = 30,
        project_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Run a full analysis for a single cloud provider.
        Returns an AnalysisResult dataclass ready for the API adapter.
        """
        with TimedOperation(logger, f"analyze:{provider_name}", provider=provider_name):
            provider = ProviderFactory.get_provider(
                provider_name,
                project_id=project_id,
                subscription_id=subscription_id,
            )

            # — Fetch data concurrently ——————————————————————————————
            costs_task = asyncio.create_task(_safe(provider.get_costs(days), []))
            infra_task = asyncio.create_task(_safe(provider.get_infrastructure(), []))

            costs, resources = await asyncio.gather(costs_task, infra_task)

            # — Build daily trends from NormalizedCost list ——————————
            daily_map: Dict[str, float] = {}
            total_cost = 0.0
            cost_by_service: Dict[str, float] = {}

            for c in costs:
                day = c.timestamp.strftime("%Y-%m-%d") if hasattr(c.timestamp, "strftime") else str(c.timestamp)[:10]
                daily_map[day] = daily_map.get(day, 0.0) + c.cost
                total_cost += c.cost
                cost_by_service[c.service] = cost_by_service.get(c.service, 0.0) + c.cost

            daily_trends = [{"date": d, "amount": round(v, 4)} for d, v in sorted(daily_map.items())]

            # — Cost drivers (top services) ————————————————————————
            cost_drivers = sorted(
                [{"service": svc, "cost": round(amt, 4)} for svc, amt in cost_by_service.items()],
                key=lambda x: x["cost"],
                reverse=True,
            )[:10]

            # — Resource type breakdown ————————————————————————————
            resource_types: Dict[str, int] = {}
            running_count = 0
            high_cost: List[Dict[str, Any]] = []

            for r in resources:
                if isinstance(r, Resource):
                    rtype = r.type or "unknown"
                    resource_types[rtype] = resource_types.get(rtype, 0) + 1
                    if r.state and r.state.upper() in ("RUNNING", "ACTIVE", "ONLINE"):
                        running_count += 1
                    if r.cost_30d and r.cost_30d > 10:
                        high_cost.append({"id": r.id, "name": r.name, "type": r.type, "cost_30d": r.cost_30d})

            return AnalysisResult(
                meta={
                    "provider": provider_name,
                    "period_days": str(days),
                    "generated_at": datetime.utcnow().isoformat(),
                },
                summary={
                    "total_cost": round(total_cost, 4),
                    "currency": "USD",
                    "resource_count": len(resources),
                },
                executive_summary={
                    "total_spend": round(total_cost, 4),
                    "risk_score": 0,
                    "anomaly_count": 0,
                    "active_recommendations": 0,
                },
                trends={},
                daily_trends=daily_trends,
                anomalies=[],
                forecast={},
                governance_issues=[],
                optimizations=[],
                resources=resources,
                cost_drivers=cost_drivers,
                resource_types=resource_types,
                running_count=running_count,
                high_cost_resources=sorted(high_cost, key=lambda x: x["cost_30d"], reverse=True)[:20],
                idle_resources=[],
                waste_findings=[],
            )

    async def aggregate_analysis(
        self,
        providers: List[str],
        days: int = 30,
        subscription_id: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Run analysis across multiple providers and delegate merging
        to AggregationEngine.
        """
        with TimedOperation(logger, "aggregate_analysis", provider=",".join(providers)):
            tasks = [
                self.analyze(p, days=days, subscription_id=subscription_id)
                for p in providers
            ]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out failures
            valid_results = []
            for res in raw_results:
                if isinstance(res, Exception):
                    logger.error(f"Provider failed during aggregate: {res}")
                else:
                    valid_results.append(res)

            return self._aggregator.merge(valid_results)

    # — MCP-compatible helpers ————————————————————————————————

    async def run_analytics_engines(self) -> Dict[str, Any]:
        """Stub for MCP server compatibility. Returns a no-op summary."""
        return {
            "anomalies_detected": 0,
            "forecasts_generated": 0,
            "recommendations_found": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "No DB-backed engines — call /api/analyze for live provider data.",
        }

    async def get_dashboard_data(self, days: int = 30) -> Dict[str, Any]:
        """Stub for MCP server compatibility."""
        return {
            "meta": {"period": f"{days} days", "generated_at": datetime.utcnow().isoformat()},
            "summary": {"total_cost": 0, "risk_score": 0, "currency": "USD"},
            "executive_summary": {"total_spend": 0, "risk_score": 0, "anomaly_count": 0, "active_recommendations": 0},
            "daily_trends": [],
            "cost_drivers": [],
            "anomalies": [],
            "recommendations": [],
            "note": "Call /api/analyze?provider=gcp|aws|azure for live data.",
        }


# — Utility ———————————————————————————————————————————————

async def _safe(coro, default):
    """Await a coroutine, return default on any exception."""
    try:
        return await coro
    except Exception as e:
        logger.warning(f"Provider call failed (returning default): {e}")
        return default
