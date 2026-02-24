from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Any, List

@dataclass
class NormalizedCost:
    """
    Unified Billing Normalization Object.
    All analytics, scoring, forecasting, and policies must operate on this structure.
    """
    provider: str
    service: str
    region: str
    resource_id: str
    cost: float
    currency: str
    timestamp: datetime
    # Identity Hierarchy
    account_id: Optional[str] = None       # AWS Account ID
    subscription_id: Optional[str] = None  # Azure Subscription ID
    project_id: Optional[str] = None       # GCP Project ID
    # Context
    team: Optional[str] = None
    business_unit: Optional[str] = None
    environment: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class Resource:
    """
    Unified Resource Model (Tri-Cloud).
    Captures state, utilization, and risk for any cloud resource.
    """
    # Identity
    id: str
    name: str
    type: str
    provider: str  # aws, gcp, azure
    region: Optional[str] = None
    account_id: Optional[str] = None
    subscription_id: Optional[str] = None
    project_id: Optional[str] = None
    
    # Lifecycle
    creation_date: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    state: Optional[str] = None                 # RUNNING, STOPPED, TERMINATED, etc.
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    class_type: Optional[str] = None            # e.g., t3.micro, n1-standard-1
    external_ip: Optional[str] = None
    
    # Metrics (Averages over last window)
    cpu_avg: Optional[float] = None
    memory_avg: Optional[float] = None
    network_io: Optional[float] = None
    disk_io: Optional[float] = None
    
    # Financials
    cost_30d: Optional[float] = None
    currency: Optional[str] = None
    
    # Intelligence
    risk_score: int = 0
    efficiency_score: int = 0
    idle_score: Optional[int] = None
    waste_reasons: List[str] = field(default_factory=list)
    optimizations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Graph
    dependencies: List[str] = field(default_factory=list) # List of resource IDs this resource depends on

@dataclass
class AnalysisResult:
    meta: Dict[str, str]
    summary: Dict[str, Any]
    executive_summary: Dict[str, Any]
    trends: Any # Summary dict from AnalyticsEngine
    daily_trends: List[Dict[str, Any]] # Raw daily breakdown for charts
    anomalies: List[Dict]
    forecast: Dict
    governance_issues: List[Dict]
    optimizations: List[Dict]
    resources: List[Resource]
    # Optional enrichment for UI/insights
    cost_drivers: List[Dict[str, Any]] = field(default_factory=list)       # top services/categories by cost
    resource_types: Dict[str, int] = field(default_factory=dict)           # counts by type
    running_count: int = 0                                                 # running VMs/instances (best-effort)
    high_cost_resources: List[Dict[str, Any]] = field(default_factory=list)
    idle_resources: List[Dict[str, Any]] = field(default_factory=list)
    waste_findings: List[Dict[str, Any]] = field(default_factory=list)
