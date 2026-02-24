from typing import Dict, Any
from dataclasses import asdict
from opsyield.core.models import AnalysisResult
from opsyield.core.logging import get_logger

logger = get_logger(__name__)

def adapt_analysis_result(result: AnalysisResult) -> Dict[str, Any]:
    """
    Adapts the domain AnalysisResult to the schema expected by the Frontend.
    
    Why:
    The frontend expects 'trends' to be an array of daily costs for charting.
    The domain Orchestrator returns 'trends' as a statistical summary dict,
    and puts daily data in 'daily_trends'.
    
    This adapter performs the mapping to prevent frontend breakage.
    """
    logger.info("Adapting analysis result...")
    # Convert dataclass to dict
    data = asdict(result)
    
    # Map daily_trends -> trends (for Frontend Chart)
    # The frontend expects: trends: Array<{ date: string, amount: number }>
    daily_trends = data.get("daily_trends", [])
    logger.info(f"Docs in daily_trends: {len(daily_trends) if isinstance(daily_trends, list) else 'Not a list'}")
    
    # Defensive coding: Ensure it's a list
    if not isinstance(daily_trends, list):
        daily_trends = []
        
    # Map raw trends (summary) to a new field in case it's needed, 
    # or just let it be overwritten if frontend doesn't use the summary in that field.
    # Frontend likely uses 'trends' for the chart only.
    # We will preserve the summary as 'trends_summary' just in case.
    trends_summary = data.get("trends", {})
    
    data["trends"] = daily_trends
    data["trends_summary"] = trends_summary
    
    # Clean up domain-only fields if necessary
    if "daily_trends" in data:
        del data["daily_trends"]

    # Ensure governance_issues exists (aliased as governance_violations in some frontend logic?)
    # Frontend might expect 'governance_violations' in some places based on previous mocks.
    # The Orchestrator returns 'governance_issues'.
    # We'll provide both or ensure the right one is there.
    # Checking prompt: "Ensure: governance_violations key exists."
    if "governance_violations" not in data:
        data["governance_violations"] = data.get("governance_issues", [])
    
    # Ensure 'forecast' is always an array for ForecastChart
    # The Orchestrator returns forecast as a Dict, but the frontend ForecastChart
    # passes it directly to recharts BarChart which requires an array.
    forecast = data.get("forecast", {})
    if isinstance(forecast, dict):
        # Convert dict forecast to array format for recharts
        # If forecast has monthly data, wrap it; otherwise provide empty array
        if forecast:
            # Try to build array from forecast dict keys
            forecast_arr = []
            for key, val in forecast.items():
                if isinstance(val, dict):
                    forecast_arr.append({"month": key, **val})
                elif isinstance(val, (int, float)):
                    forecast_arr.append({"month": key, "predicted_cost": val})
            data["forecast"] = forecast_arr if forecast_arr else []
        else:
            data["forecast"] = []
    elif not isinstance(forecast, list):
        data["forecast"] = []
        
    return data
