from typing import List, Optional

from ..core.models import Resource


class RecommendationEngine:

    def build(self, resource: Resource, idle_score: int, suggestion: Optional[str], savings: float) -> List[str]:

        recommendations = []

        if idle_score >= 70:
            recommendations.append("Consider stopping this instance")

        if suggestion:
            recommendations.append(
                f"Downsize to {suggestion} to save approx ${savings}/month"
            )

        return recommendations
