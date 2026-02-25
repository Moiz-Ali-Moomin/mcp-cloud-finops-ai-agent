from typing import Optional

from ..core.models import Resource


class IdleScorer:

    def calculate_score(self, resource: Resource, cpu_avg: Optional[float] = None) -> int:
        score = 0
        state = (resource.state or "").lower()

        # Stopped instances with cost > 0
        if "stop" in state or "terminated" in state:
            if (resource.cost_30d or 0) > 0:
                score += 50

        # No external IP (often internal/test)
        if not resource.external_ip:
            score += 20

        # Low CPU (if available)
        effective_cpu = cpu_avg if cpu_avg is not None else resource.cpu_avg
        if effective_cpu is not None and effective_cpu < 0.05 and "running" in state:
            score += 50

        # Long running non-prod (heuristic via creation_date)
        # Note: days_running is not on Resource, but can be computed from creation_date
        # For now, skip this heuristic unless extended.

        # Keyword heuristics
        name = (resource.name or "").lower()
        if any(x in name for x in ["test", "dev", "tmp", "temp"]):
            score += 20

        return min(100, score)
