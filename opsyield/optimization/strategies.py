from typing import List, Dict
from ..core.models import NormalizedCost
from ..core.interfaces import OptimizationStrategy

class IdleScorer(OptimizationStrategy):
    """
    Identifies idle resources based on tags and cost patterns.
    Phase 1: Simple logic based on metadata/mock tags.
    """
    def analyze(self, cost_item: NormalizedCost) -> Dict:
        # Phase 1 Logic: If tagged 'idle', it's idle. 
        # Or if cost is low but constant (simplification).
        score = 0
        reason = []
        
        if cost_item.tags.get("idle") == "true":
            score = 100
            reason.append(" Explicitly tagged as idle")
        
        # Heuristic: Dev environments costing > $50/day might be wasteful
        if cost_item.environment == "development" and cost_item.cost > 50.0:
            score += 20
            reason.append("High cost for development resource")

        if score > 0:
            return {
                "check_name": "IdleResource",
                "score": min(score, 100),
                "reason": "; ".join(reason),
                "potential_savings": cost_item.cost # Assuming 100% savings if idle
            }
        return None

class OptimizationEngine:
    """
    Orchestrates optimization strategies against unified cost data.
    """
    def __init__(self):
        self.strategies: List[OptimizationStrategy] = [
            IdleScorer()
        ]

    def analyze(self, costs: List[NormalizedCost]) -> List[Dict]:
        results = []
        for item in costs:
            item_optimizations = []
            for strategy in self.strategies:
                res = strategy.analyze(item)
                if res:
                    # Enrich result with resource details
                    res["resource_id"] = item.resource_id
                    res["service"] = item.service
                    res["cost"] = item.cost
                    item_optimizations.append(res)
            
            if item_optimizations:
                results.extend(item_optimizations)
        
        # Sort by potential savings descending
        results.sort(key=lambda x: x.get("potential_savings", 0), reverse=True)
        return results
