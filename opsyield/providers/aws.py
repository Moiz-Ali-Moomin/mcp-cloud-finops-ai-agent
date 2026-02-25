"""
AWS Provider -- Production-grade cloud status detection.

Uses subprocess.run(shell=True) for Windows .cmd compatibility.
Authentication is determined by CLI exit code of `aws sts get-caller-identity`.
"""
import os
import shutil
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from ..core.models import NormalizedCost, Resource
from ..core.logging import get_logger
from .cli_utils import run_cli, parse_json

logger = get_logger(__name__)


class AWSProvider:
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        self.region = region
        self.profile = profile

    def get_status_sync(self) -> Dict[str, Any]:
        """
        Synchronous status check -- called via asyncio.to_thread().

        Authentication logic:
          1. shutil.which("aws") -> installed
          2. aws sts get-caller-identity --output json
             -> exit code 0 -> authenticated
             -> Parse Account field from JSON stdout
        """
        status: Dict[str, Any] = {
            "installed": False,
            "authenticated": False,
            "account": None,
            "error": None,
            "debug": {},
        }

        # -- 1. Installation check --
        aws_path = shutil.which("aws")
        if not aws_path:
            status["error"] = "AWS CLI not found on PATH"
            status["debug"]["which"] = None
            return status
        status["installed"] = True
        status["debug"]["which"] = aws_path

        # -- 2. Authentication check via STS --
        sts_cmd = "aws sts get-caller-identity --output json"
        sts = run_cli(sts_cmd, tag="AWS")
        status["debug"]["sts"] = {
            "stdout": sts["stdout"][:300],
            "stderr": sts["stderr"][:300],
            "returncode": sts["returncode"],
        }

        if sts["ok"]:
            # CLI exit code 0 -> authenticated
            status["authenticated"] = True
            parsed = parse_json(sts["stdout"])
            if isinstance(parsed, dict):
                status["account"] = parsed.get("Account")
                status["debug"]["arn"] = parsed.get("Arn", "")
        else:
            status["error"] = sts["stderr"] or "AWS credentials not configured"

        # -- 3. Environment hints --
        status["debug"]["env"] = {
            "AWS_PROFILE": os.environ.get("AWS_PROFILE", "(not set)"),
            "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION", "(not set)"),
            "AWS_ACCESS_KEY_ID": "***set***" if os.environ.get("AWS_ACCESS_KEY_ID") else "(not set)",
        }

        return status

    async def get_status(self) -> Dict[str, Any]:
        """Async wrapper -- runs blocking subprocess in a thread."""
        return await asyncio.to_thread(self.get_status_sync)

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        from ..billing.aws import AWSBillingProvider
        billing = AWSBillingProvider(region=self.region)
        return await billing.get_costs(days)

    async def get_infrastructure(self) -> List[Resource]:
        """Discovers infrastructure using modular collectors."""
        if not HAS_BOTO3:
            return []

        from ..collectors.aws.ec2 import EC2Collector
        from ..collectors.aws.s3 import S3Collector
        from ..collectors.aws.rds import RDSCollector

        collectors = [
            EC2Collector(region=self.region),
            S3Collector(region=self.region),
            RDSCollector(region=self.region)
        ]

        results = await asyncio.gather(*[c.collect() for c in collectors], return_exceptions=True)

        all_resources = []
        for res in results:
            if isinstance(res, list):
                all_resources.extend(res)
            else:
                logger.error(f"[AWS] Collector failed: {res}")

        return all_resources

    def get_resource_metadata(self, resource_id: str) -> dict:
        return {"id": resource_id, "provider": "aws"}

    async def get_utilization_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        if not HAS_BOTO3:
            return resources
        from ..collectors.aws.metrics import AWSMetricsCollector
        collector = AWSMetricsCollector(region=self.region)
        return await collector.collect_metrics(resources, period_days)
