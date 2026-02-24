"""
OpsYield Core — Domain layer.

Exports the primary classes used across the application.
"""

from .models import NormalizedCost, Resource, AnalysisResult
from .interfaces import BaseProvider, OptimizationStrategy
from .orchestrator import Orchestrator
from .aggregation import AggregationEngine
from .snapshot import SnapshotManager, DiffResult
from .cloud_detection import CloudDetector
from .scheduler import Scheduler
from .logging import get_logger, set_correlation_id, get_correlation_id, TimedOperation

__all__ = [
    "NormalizedCost",
    "Resource",
    "AnalysisResult",
    "BaseProvider",
    "OptimizationStrategy",
    "Orchestrator",
    "AggregationEngine",
    "SnapshotManager",
    "DiffResult",
    "CloudDetector",
    "Scheduler",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "TimedOperation",
]
