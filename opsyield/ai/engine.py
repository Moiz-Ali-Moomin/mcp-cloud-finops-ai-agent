from typing import Dict, Any, List

class AIInsightEngine:
    """
    Abstractions for generating AI prompts from financial data.
    """

    def build_system_prompt(self) -> str:
        return (
            "You are a Cloud Financial Operations (FinOps) expert. "
            "Analyze the provided cost data, anomalies, and policy violations. "
            "Provide actionable recommendations to reduce spend and mitigate risk. "
            "Focus on high-impact changes first."
        )

    def build_user_prompt(self, 
                          executive_summary: Dict[str, Any], 
                          anomalies: List[Dict], 
                          violations: List[Dict]) -> str:
        
        prompt = f"""
        Analyze the following cloud cost report:

        1. Executive Summary:
        - Total Spend: ${executive_summary.get('total_spend', 0):.2f}
        - Waste: {executive_summary.get('waste_percentage', 0)}%
        - Risk Score: {executive_summary.get('risk_score', 0)} ({executive_summary.get('exposure_category', 'UNKNOWN')})
        
        2. Top Anomalies:
        """
        
        for a in anomalies[:5]:
             prompt += f"   - {a.get('service')} on {a.get('date')}: ${a.get('cost', 0):.2f} (Z-Score: {a.get('z_score', 0)})\n"
        
        prompt += "\n3. Policy Violations:\n"
        for v in violations[:5]:
            prompt += f"   - {v.get('policy')} in {v.get('scope')}: {v.get('action')}\n"

        prompt += "\nProvide 3 specific actions I should take immediately."
        return prompt
