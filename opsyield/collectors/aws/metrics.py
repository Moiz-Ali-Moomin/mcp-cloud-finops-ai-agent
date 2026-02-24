from typing import List, Dict
import boto3
from datetime import datetime, timedelta
import asyncio
from ...core.models import Resource
from ...core.logging import get_logger

logger = get_logger(__name__)

class AWSMetricsCollector:
    def __init__(self, region: str):
        self.region = region

    async def collect_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        return await asyncio.to_thread(self._sync_collect_metrics, resources, period_days)

    def _sync_collect_metrics(self, resources: List[Resource], period_days: int) -> List[Resource]:
        """
        Fetch CPU, Network, Disk metrics for EC2/RDS using CloudWatch.
        Uses GetMetricData for efficiency (batching).
        """
        try:
            session = boto3.Session(region_name=self.region)
            cloudwatch = session.client("cloudwatch")
        except Exception as e:
            logger.error(f"Failed to create CloudWatch client: {e}")
            return resources

        # Filter for EC2 instances
        ec2_resources = [r for r in resources if r.type == "ec2_instance" and r.state == "running"]
        if not ec2_resources:
            return resources

        # CloudWatch Batch Limit is 500. We fetch CPUUtilization for each.
        # We process in chunks.
        
        chunk_size = 100 # Safe chunk size
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        for i in range(0, len(ec2_resources), chunk_size):
            chunk = ec2_resources[i:i+chunk_size]
            queries = []
            
            for idx, res in enumerate(chunk):
                queries.append({
                    'Id': f'cpu_{idx}',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': 'CPUUtilization',
                            'Dimensions': [{'Name': 'InstanceId', 'Value': res.id}]
                        },
                        'Period': 86400 * period_days, # Single datapoint for the average over period? Or daily?
                        # Requirement: "Average over last window". Let's get one average number.
                        'Stat': 'Average',
                    },
                    'ReturnData': True,
                    'Label': res.id
                })

            try:
                # max 500 queries
                response = cloudwatch.get_metric_data(
                    MetricDataQueries=queries,
                    StartTime=start_time,
                    EndTime=end_time,
                )
                
                # Map results back
                for metric_result in response.get("MetricDataResults", []):
                    # Label is res.id
                    r_id = metric_result.get("Label")
                    values = metric_result.get("Values", [])
                    if values:
                        avg_cpu = sum(values) / len(values)
                        # Find resource
                        for r in chunk:
                            if r.id == r_id:
                                r.cpu_avg = round(avg_cpu, 2)
                                break
            except Exception as e:
                logger.error(f"CloudWatch GetMetricData failed: {e}")
                
        return resources
