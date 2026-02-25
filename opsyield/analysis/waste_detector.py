from typing import List, Dict, Any
from datetime import datetime, timezone

from ..core.models import Resource


class WasteDetector:

    MAX_RUNTIME_DAYS = 14  # Lowered threshold for warning

    def detect(self, resources: List[Resource]) -> List[Dict[str, Any]]:
        waste = []
        now = datetime.now(timezone.utc)

        for r in resources:
            reasons = []
            name = (r.name or "").lower()
            state = (r.state or "").lower()
            cost = r.cost_30d or 0

            # 1. Stopped but costing money (Zombie resources)
            if ("stop" in state or "terminated" in state) and cost > 1.0:
                reasons.append(f"Stopped but incurring cost (${cost:.2f})")

            # 2. Old temporary resources
            created_at = r.creation_date
            if created_at:
                days_running = (now - created_at).days
                if days_running > self.MAX_RUNTIME_DAYS:
                    if any(x in name for x in ["tmp", "temp", "test", "poc"]):
                         reasons.append(f"Temporary resource running for {days_running} days")

            # 3. Orphaned IPs
            if r.type == "ip_address" and state == "reserved":
                 reasons.append("Unattached IP address")

            if reasons:
                waste.append({
                    "name": r.name,
                    "type": r.type or "unknown",
                    "reasons": reasons,
                    "cost_30d": cost
                })

        return waste
