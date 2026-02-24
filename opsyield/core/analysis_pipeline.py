from opsyield.providers.base import get_provider
from opsyield.analysis.cost_analyzer import CostAnalyzer
from opsyield.analysis.waste_detector import WasteDetector
from opsyield.analysis.idle_scoring import IdleScorer
from opsyield.analysis.rightsizer import Rightsizer
from opsyield.analysis.recommendations import RecommendationEngine
from opsyield.analysis.savings import estimate_savings


class CloudLensEngine:

    def __init__(self, provider: str, project_id=None):
        self.provider = get_provider(provider, project_id)

    def run(self):

        # Step 1 â€” Discover resources
        resources = self.provider.discover()

        # Step 2 â€” Cost calculation
        analyzer = CostAnalyzer(self.provider)
        cost_data = analyzer.calculate(resources)

        # Step 3 â€” Basic waste detection
        waste_detector = WasteDetector()
        waste = waste_detector.detect(resources)

        # Step 4 â€” Advanced optimization logic
        scorer = IdleScorer()
        rightsizer = Rightsizer()
        recommender = RecommendationEngine()

        advanced_results = []

        for r in resources:

            current_cost = self.provider.price(r)

            cpu_avg = 0  # Placeholder until monitoring integrated

            idle_score = scorer.calculate_score(r, cpu_avg)

            suggestion = rightsizer.suggest(r["type"], cpu_avg)

            new_cost = (
                self.provider.price({"type": suggestion})
                if suggestion
                else current_cost
            )

            savings = estimate_savings(current_cost, new_cost)

            recs = recommender.build(r, idle_score, suggestion, savings)

            if recs:
                advanced_results.append({
                    "name": r["name"],
                    "type": r["type"],
                    "idle_score": idle_score,
                    "recommendations": recs
                })

        return {
            "resources": len(resources),
            "cost": cost_data,
            "waste": waste,
            "advanced": advanced_results
        }
