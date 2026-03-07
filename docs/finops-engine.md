# FinOps Analysis & Decision Engine

The FinOps engine is the analytical core of OpsYield. It is responsible for taking raw billing data and infrastructure telemetry, and turning it into actionable intelligence.

## Pipeline Overview

1.  **Ingestion**: Normalizes varied cloud data models into a unified `ResourceSnapshot` or `CostInterval`.
2.  **Enrichment**: Adds tagging data, pricing tiers, and amortized cost calculations.
3.  **Heuristic Analysis**: Executes policy-based logic against the enriched data.
4.  **Recommendation Generation**: Outputs structured tasks (e.g., "Downsize EC2 instance i-12345 from m5.xlarge to m5.large to save $45/mo").

## Analysis Strategies

### 1. Zombie / Orphan Resource Detection
The engine queries compute APIs across all clouds to find:
- Unattached EBS/Persistent Disks.
- Elastic IPs / Static IPs not bound to active compute instances.
- Idle Load Balancers with zero backend targets or zero requests over 7 days.

### 2. Underutilized Compute (Rightsizing)
The engine analyzes trailing 14-day CPU metrics:
- If `average CPU < 5%` and `max CPU < 20%`, it categorizes the instance as **Idle**.
- If `average CPU < 20%` and `max CPU < 40%`, it categorizes the instance as **Underutilized** and simulates the cost of dropping one instance family size down.

### 3. Outlier Detection
By calculating moving averages for daily spend per cloud service, the engine flags days where spend spikes by `> X standard deviations` from the mean. This helps detect runaway lambda functions, sudden data egress spikes, or potentially compromised credentials mining cryptocurrency.

## Adding New Rules

To add a new heuristic strategy:
1. Create a new module inside `opsyield/optimization/`.
2. Implement the `BaseHeuristic` abstract class, which requires an `evaluate()` function.
3. Register the rule in the orchestrator pipeline config.
This modularity ensures the engine can continually expand its FinOps intelligence without modifying core extraction logic.
