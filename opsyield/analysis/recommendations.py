class RecommendationEngine:

    def build(self, resource, idle_score, suggestion, savings):

        recommendations = []

        if idle_score >= 70:
            recommendations.append("Consider stopping this instance")

        if suggestion:
            recommendations.append(
                f"Downsize to {suggestion} to save approx ${savings}/month"
            )

        return recommendations
