from typing import List

from ..core.models import Resource


class CostAnalyzer:
    """Calculate total cost from a list of Resource objects."""

    def calculate(self, resources: List[Resource]) -> float:
        total = 0.0
        for r in resources:
            total += r.cost_30d or 0.0
        return total
