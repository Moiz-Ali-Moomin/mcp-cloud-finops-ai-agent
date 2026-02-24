from datetime import datetime, timezone

class WasteDetector:

    MAX_RUNTIME_DAYS = 14 # Lowered threshold for warning

    def detect(self, resources):
        waste = []
        now = datetime.now(timezone.utc)

        for r in resources:
            reasons = []
            name = (r.get("name") or "").lower()
            state = (r.get("state") or "").lower()
            cost = r.get("cost_30d", 0)

            # 1. Stopped but costing money (Zombie resources)
            if ("stop" in state or "terminated" in state) and cost > 1.0:
                reasons.append(f"Stopped but incurring cost (${cost:.2f})")

            # 2. Old temporary resources
            created_at = r.get("created_at")
            if created_at:
                days_running = (now - created_at).days
                if days_running > self.MAX_RUNTIME_DAYS:
                    if any(x in name for x in ["tmp", "temp", "test", "poc"]):
                         reasons.append(f"Temporary resource running for {days_running} days")

            # 3. Orphaned IPs (Heuristic: name contains 'ip' but not attached? 
            # Hard to know without specific type, but generic checks help)
            if r.get("type") == "ip_address" and r.get("state") == "reserved":
                 reasons.append("Unattached IP address")

            if reasons:
                waste.append({
                    "name": r["name"],
                    "type": r.get("type", "unknown"),
                    "reasons": reasons,
                    "cost_30d": cost
                })

        return waste
