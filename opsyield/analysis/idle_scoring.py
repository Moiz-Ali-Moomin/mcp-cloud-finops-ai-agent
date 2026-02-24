class IdleScorer:

    def calculate_score(self, resource, cpu_avg=None):
        score = 0
        state = (resource.get("state") or "").lower()
        r_type = (resource.get("type") or "").lower()

        # Stopped instances are technically "idle" regarding compute, 
        # but might be intentional. If they have cost > 0 (storage), 
        # we flag them.
        if "stop" in state or "terminated" in state:
            if resource.get("cost_30d", 0) > 0:
                score += 50 # High score for paying for stopped things
        
        # No external IP (often internal/test)
        if not resource.get("external_ip"):
            score += 20

        # Low CPU (if available)
        if cpu_avg is not None and cpu_avg < 0.05 and "running" in state:
            score += 50

        # Long running non-prod (heuristic)
        days_running = resource.get("days_running", 0)
        if days_running > 30:
            score += 10
        
        # Keyword heuristics
        name = (resource.get("name") or "").lower()
        if any(x in name for x in ["test", "dev", "tmp", "temp"]):
            score += 20

        return min(100, score)
