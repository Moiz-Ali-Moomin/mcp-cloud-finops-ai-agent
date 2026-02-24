"""
OpsYield Cross-Provider Aggregation Engine.

Extracted from Orchestrator to enforce Single Responsibility.
Merges AnalysisResult objects from multiple cloud providers into
a unified multi-cloud view.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .models import AnalysisResult, Resource
from .logging import get_logger

logger = get_logger(__name__)


class AggregationEngine:
    """
    Merges analysis results from multiple providers into a single
    unified AnalysisResult.
    """

    def merge(self, results: List[AnalysisResult]) -> AnalysisResult:
        """
        Merge multiple per-provider AnalysisResult objects into one.
        Handles cost summation, resource union, anomaly dedup, and
        forecast combination.
        """
        if not results:
            return self._empty_result()

        if len(results) == 1:
            return results[0]

        logger.info(f"Aggregating results from {len(results)} providers")

        all_resources = []
        total_cost = 0.0
        total_waste = 0.0
        all_anomalies = []
        all_governance = []
        all_optimizations = []
        all_daily_trends = []
        all_cost_drivers = []
        all_high_cost = []
        all_idle = []
        all_waste_findings = []
        resource_types: Dict[str, int] = {}
        running_count = 0
        providers_seen = []

        for r in results:
            provider = r.meta.get("provider", "unknown")
            providers_seen.append(provider)

            # Resources
            all_resources.extend(r.resources)

            # Cost
            total_cost += r.summary.get("total_cost", 0)
            total_waste += r.summary.get("total_waste", 0)

            # Anomalies — tag with provider
            for a in r.anomalies:
                a_copy = {**a, "provider": provider}
                all_anomalies.append(a_copy)

            # Governance
            all_governance.extend(r.governance_issues)

            # Optimizations
            all_optimizations.extend(r.optimizations)

            # Daily trends — tag with provider
            for trend in r.daily_trends:
                trend_copy = {**trend, "provider": provider}
                all_daily_trends.append(trend_copy)

            # Enrichments
            all_cost_drivers.extend(r.cost_drivers)
            all_high_cost.extend(r.high_cost_resources)
            all_idle.extend(r.idle_resources)
            all_waste_findings.extend(r.waste_findings)
            running_count += r.running_count

            # Resource type counts
            for rtype, count in r.resource_types.items():
                resource_types[rtype] = resource_types.get(rtype, 0) + count

        # Build merged forecast
        merged_forecast = self._merge_forecasts([r.forecast for r in results])

        # Build executive summary
        risk_scores = [
            r.executive_summary.get("risk_score", 0)
            for r in results
            if r.executive_summary
        ]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        merged = AnalysisResult(
            meta={
                "provider": ",".join(providers_seen),
                "type": "multi-cloud-aggregate",
                "generated_at": datetime.utcnow().isoformat(),
                "source_count": str(len(results)),
            },
            summary={
                "total_cost": round(total_cost, 2),
                "total_waste": round(total_waste, 2),
                "resource_count": len(all_resources),
                "providers": providers_seen,
                "savings_potential": round(total_waste * 0.6, 2),
            },
            executive_summary={
                "risk_score": round(avg_risk, 1),
                "headline": f"Multi-cloud analysis across {', '.join(providers_seen)}",
                "total_cost": round(total_cost, 2),
                "provider_count": len(providers_seen),
            },
            trends={"aggregated": True, "provider_count": len(results)},
            daily_trends=sorted(
                all_daily_trends,
                key=lambda x: x.get("date", ""),
            ),
            anomalies=all_anomalies,
            forecast=merged_forecast,
            governance_issues=all_governance,
            optimizations=sorted(
                all_optimizations,
                key=lambda x: x.get("potential_savings", 0),
                reverse=True,
            ),
            resources=all_resources,
            cost_drivers=sorted(
                all_cost_drivers,
                key=lambda x: x.get("cost", 0),
                reverse=True,
            )[:20],
            resource_types=resource_types,
            running_count=running_count,
            high_cost_resources=sorted(
                all_high_cost,
                key=lambda x: x.get("cost", 0),
                reverse=True,
            )[:20],
            idle_resources=all_idle,
            waste_findings=all_waste_findings,
        )

        logger.info(
            f"Aggregation complete: {len(all_resources)} resources, "
            f"${total_cost:,.2f} total cost across {len(providers_seen)} providers"
        )

        return merged

    def _merge_forecasts(self, forecasts: List[Dict]) -> Dict:
        """Combine per-provider forecasts into one."""
        if not forecasts:
            return {}

        total_predicted = sum(
            f.get("predicted_additional_spend", 0) for f in forecasts if f
        )
        return {
            "predicted_additional_spend": round(total_predicted, 2),
            "source_forecasts": len([f for f in forecasts if f]),
            "confidence": "low",
        }

    def _empty_result(self) -> AnalysisResult:
        """Return a zero-value AnalysisResult."""
        return AnalysisResult(
            meta={"provider": "none", "type": "empty"},
            summary={"total_cost": 0, "resource_count": 0},
            executive_summary={"risk_score": 0},
            trends={},
            daily_trends=[],
            anomalies=[],
            forecast={},
            governance_issues=[],
            optimizations=[],
            resources=[],
        )
