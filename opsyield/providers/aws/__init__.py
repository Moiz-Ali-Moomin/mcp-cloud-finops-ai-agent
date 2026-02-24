"""
AWS Provider â€” exposed at the package level so factory.py can do:
    from .aws import AWSProvider
"""
import json
import logging
import os
import shutil
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from ...core.models import NormalizedCost, Resource

logger = logging.getLogger("opsyield-aws")


def _clean_env() -> dict:
    env = os.environ.copy()
    env.pop("PAGER", None)
    return env


def _run(cmd: str, timeout: int = 15) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout,
            env=_clean_env(),
        )
        logger.info(f"[AWS] cmd={cmd!r} rc={result.returncode}")
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}


def _parse_json(raw: str):
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


class AWSProvider:
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        self.region = region
        self.profile = profile

    def get_status_sync(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "installed": False,
            "authenticated": False,
            "account": None,
            "error": None,
            "debug": {},
        }

        aws_path = shutil.which("aws")
        if not aws_path:
            status["error"] = "AWS CLI not found on PATH"
            return status
        status["installed"] = True
        status["debug"]["which"] = aws_path

        sts = _run("aws sts get-caller-identity --output json")
        status["debug"]["sts"] = {
            "stdout": sts["stdout"][:300],
            "stderr": sts["stderr"][:300],
            "returncode": sts["returncode"],
        }

        if sts["ok"]:
            status["authenticated"] = True
            parsed = _parse_json(sts["stdout"])
            if isinstance(parsed, dict):
                status["account"] = parsed.get("Account")
                status["debug"]["arn"] = parsed.get("Arn", "")
        else:
            status["error"] = sts["stderr"] or "AWS credentials not configured"

        status["debug"]["env"] = {
            "AWS_PROFILE": os.environ.get("AWS_PROFILE", "(not set)"),
            "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION", "(not set)"),
            "AWS_ACCESS_KEY_ID": "***set***" if os.environ.get("AWS_ACCESS_KEY_ID") else "(not set)",
        }
        return status

    async def get_status(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_status_sync)

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        """Fetch costs via AWS Cost Explorer (boto3)."""
        if not HAS_BOTO3:
            logger.warning("[AWS] boto3 not installed â€” skipping cost fetch")
            return []
        try:
            from ...billing.aws import AWSBillingProvider
            billing = AWSBillingProvider(region=self.region)
            return await billing.get_costs(days)
        except Exception as e:
            logger.error(f"[AWS] Cost fetch failed: {e}")
            return []

    async def get_infrastructure(self) -> List[Resource]:
        if not HAS_BOTO3:
            return []
        try:
            from ...collectors.aws.ec2 import EC2Collector
            from ...collectors.aws.s3 import S3Collector
            from ...collectors.aws.rds import RDSCollector
            collectors = [
                EC2Collector(region=self.region),
                S3Collector(region=self.region),
                RDSCollector(region=self.region),
            ]
            results = await asyncio.gather(*[c.collect() for c in collectors], return_exceptions=True)
            resources = []
            for res in results:
                if isinstance(res, list):
                    resources.extend(res)
                else:
                    logger.error(f"[AWS] Collector failed: {res}")
            return resources
        except Exception as e:
            logger.error(f"[AWS] Infrastructure discovery failed: {e}")
            return []

    def get_resource_metadata(self, resource_id: str) -> dict:
        return {"id": resource_id, "provider": "aws"}

    async def get_utilization_metrics(self, resources: List[Resource], period_days: int = 7) -> List[Resource]:
        if not HAS_BOTO3:
            return resources
        try:
            from ...collectors.aws.metrics import AWSMetricsCollector
            collector = AWSMetricsCollector(region=self.region)
            return await collector.collect_metrics(resources, period_days)
        except Exception as e:
            logger.error(f"[AWS] Metrics failed: {e}")
            return resources
