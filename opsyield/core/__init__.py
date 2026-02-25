"""
OpsYield Core -- Domain layer.

Exports the primary classes used across the application.

NOTE: Orchestrator is NOT imported here to avoid circular imports
(it depends on providers which depend on core). Import directly:
    from opsyield.core.orchestrator import Orchestrator
"""

from .models import NormalizedCost, Resource, AnalysisResult, OptimizationStrategy
from .aggregation import AggregationEngine
from .snapshot import SnapshotManager, DiffResult
from .logging import get_logger, set_correlation_id, get_correlation_id, TimedOperation

__all__ = [
    "NormalizedCost",
    "Resource",
    "AnalysisResult",
    "OptimizationStrategy",
    "AggregationEngine",
    "SnapshotManager",
    "DiffResult",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "TimedOperation",
]
