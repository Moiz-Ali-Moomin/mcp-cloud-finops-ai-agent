import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .logging import get_logger

logger = get_logger(__name__)

@dataclass
class DiffResult:
    baseline_path: str
    is_regression: bool = False
    cost_increase_pct: float = 0.0
    risk_score_change: float = 0.0
    new_anomalies: int = 0
    new_violations: int = 0
    details: List[str] = field(default_factory=list)

class SnapshotManager:
    """
    Manages saving, loading, and comparing analysis snapshots for CI/CD guardrails.
    """

    @staticmethod
    def save(data: Dict[str, Any], path: str):
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Snapshot saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            raise

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load snapshot from {path}: {e}")
            raise

    @staticmethod
    def compare(baseline: Dict[str, Any], current: Dict[str, Any], 
                cost_threshold_pct: float = 0.0, 
                fail_on_policy: bool = False) -> DiffResult:
        
        result = DiffResult(baseline_path="baseline")
        
        # 1. Cost Comparison
        base_cost = baseline.get("summary", {}).get("total_cost", 0)
        curr_cost = current.get("summary", {}).get("total_cost", 0)
        
        # Handle zero division
        if base_cost > 0:
            result.cost_increase_pct = ((curr_cost - base_cost) / base_cost) * 100
        elif curr_cost > 0:
            result.cost_increase_pct = 100.0
        
        if result.cost_increase_pct > cost_threshold_pct:
            result.is_regression = True
            result.details.append(f"Cost increased by {result.cost_increase_pct:.2f}% (Threshold: {cost_threshold_pct}%)")

        # 2. Risk Score Comparison
        base_risk = baseline.get("executive_summary", {}).get("risk_score", 0)
        curr_risk = current.get("executive_summary", {}).get("risk_score", 0)
        result.risk_score_change = curr_risk - base_risk
        
        if result.risk_score_change > 0:
            result.details.append(f"Risk score increased by {result.risk_score_change:.2f}")

        # 3. New Anomalies
        base_anomalies = {a.get("id") for a in baseline.get("analytics", {}).get("anomalies", [])}
        curr_anomalies_list = current.get("analytics", {}).get("anomalies", [])
        new_anomalies_count = 0
        
        for anomaly in curr_anomalies_list:
            if anomaly.get("id") not in base_anomalies:
                new_anomalies_count += 1
        
        result.new_anomalies = new_anomalies_count
        if new_anomalies_count > 0:
            result.details.append(f"Detected {new_anomalies_count} new cost anomalies.")

        # 4. New Violations
        # Assuming violations structure: { "violations": [...] }
        base_violations = len(baseline.get("governance", {}).get("violations", []))
        curr_violations = len(current.get("governance", {}).get("violations", []))
        result.new_violations = max(0, curr_violations - base_violations)

        if fail_on_policy and curr_violations > 0:
            result.is_regression = True
            result.details.append(f"Policy violations detected: {curr_violations} (Fail-on-policy is ACTIVE)")
        elif result.new_violations > 0:
             result.details.append(f"New policy violations detected: {result.new_violations}")

        return result
