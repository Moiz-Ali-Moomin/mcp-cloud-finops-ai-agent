from typing import List
import asyncio
from datetime import datetime, timedelta
from ...core.models import Resource
from ...core.logging import get_logger
from gcp.base import GCPBaseCollector

logger = get_logger(__name__)

class GCPMetricsCollector(GCPBaseCollector):
    def __init__(self, project_id: str = None):
        super().__init__(project_id)

    async def collect_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
         return await asyncio.to_thread(self._sync_collect_metrics, resources, period_days)

    def _sync_collect_metrics(self, resources: List[Resource], period_days: int) -> List[Resource]:
        """
        Fetch CPU utilization using Google Cloud Monitoring API.
        """
        try:
            from google.cloud import monitoring_v3
        except ImportError:
            logger.warning("google-cloud-monitoring not installed")
            return resources

        if not self.project_id:
            return resources

        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{self.project_id}"
        
        # We can filter by instance names
        # Filter: metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.type="gce_instance"
        
        now = time.time()
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(now)},
            "start_time": {"seconds": int(now - (period_days * 86400))}
        })
        
        # GCP Monitoring API handles aggregation
        # We want mean across the period.
        pass # Implementation stub for complex aggregation
        
        # For prototype, we'll implement a basic per-instance fetch loop or aggregated query
        # Fetching for all instances in project is efficient.
        
        filter_str = 'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.type="gce_instance"'
        
        try:
            results = client.list_time_series(
                request={
                    "name": project_name,
                    "filter": filter_str,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    "aggregation": {
                        "alignment_period": {"seconds": period_days * 86400},
                        "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN
                    }
                }
            )
            
            for result in results:
                instance_id = result.resource.labels.get("instance_id")
                if not instance_id:
                    continue
                
                # Get value
                if result.points:
                    val = result.points[0].value.double_value
                    # Map to resource
                    for r in resources:
                        if r.id == instance_id:
                            r.cpu_avg = round(val * 100, 2) # GCP returns 0-1
                            break


        except Exception as e:
            logger.error(f"GCP Monitoring failed: {e}")

        return resources

    async def collect(self) -> List[Resource]:
        return []

    async def health_check(self) -> bool:
        return True
