from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class ComparisonEngine:
    def compare_providers(self, analysis_results: List[Any]) -> Dict[str, Any]:
        """
        Compare costs and efficiency across providers.
        """
        comparison = {
            "total_spend_by_provider": {},
            "efficiency_by_provider": {},
            "resource_count_by_provider": {},
            "winner": None
        }
        
        for res in analysis_results:
            provider = res.meta.get("provider")
            comparison["total_spend_by_provider"][provider] = res.summary.get("total_cost", 0)
            comparison["resource_count_by_provider"][provider] = res.summary.get("resource_count", 0)
            # Simple efficiency metric: Cost / Resource Count (lower is better? or depends on workload)
            # This is naive but a start.
            if res.summary.get("resource_count", 0) > 0:
                 comparison["efficiency_by_provider"][provider] = res.summary.get("total_cost", 0) / res.summary.get("resource_count", 0)

        return comparison

class BudgetEngine:
    def check_budgets(self, current_spend: float, budget: float) -> Dict[str, Any]:
        """
        Check if spend is within budget and forecast burn rate.
        """
        # Simple linear projection
        now = datetime.now()
        day_of_month = now.day
        days_in_month = 30 # Approximation
        
        projected_spend = (current_spend / day_of_month) * days_in_month if day_of_month > 0 else current_spend
        
        return {
            "budget": budget,
            "current_spend": current_spend,
            "projected_spend": projected_spend,
            "is_over_budget": current_spend > budget,
            "is_projected_over_budget": projected_spend > budget,
            "burn_rate_daily": current_spend / day_of_month if day_of_month > 0 else 0
        }

class ForecastEngine:
    def forecast_spend(self, daily_history: List[Dict[str, Any]], days_ahead: int = 30) -> Dict[str, Any]:
        """
        Forecast future spend based on history.
        """
        if not daily_history:
            return {}
        
        # Simple linear regression or moving average
        values = [d["amount"] for d in daily_history]
        if len(values) < 2:
             return {"predicted_total": sum(values)}
             
        avg_daily = statistics.mean(values[-7:]) # Last 7 days average
        
        predicted_total = avg_daily * days_ahead
        
        return {
            "days_ahead": days_ahead,
            "predicted_additional_spend": predicted_total,
            "confidence": "low" # Simple heuristic
        }
