import boto3
import asyncio
from typing import List, Dict, Any

from ..base import BaseCollector
from ...core.models import Resource

class RDSCollector(BaseCollector):
    def __init__(self, region: str = "us-east-1"):
        super().__init__("aws", region)

    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            session = boto3.Session(region_name=self.region)
            rds = session.client("rds")
            paginator = rds.get_paginator("describe_db_instances")

            for page in paginator.paginate():
                for instance in page.get("DBInstances", []):
                    try:
                        r = self._parse_instance(instance)
                        resources.append(r)
                    except Exception as e:
                        self._handle_error(f"parse_rds {instance.get('DBInstanceIdentifier')}", e)
                        continue
        except Exception as e:
            self._handle_error("collect_rds", e)
        
        return resources

    def _parse_instance(self, inst: Dict[str, Any]) -> Resource:
        db_id = inst.get("DBInstanceIdentifier")
        engine = inst.get("Engine")
        status = inst.get("DBInstanceStatus")
        instance_class = inst.get("DBInstanceClass")
        allocated_storage = inst.get("AllocatedStorage")
        create_time = inst.get("InstanceCreateTime")
        is_public = inst.get("PubliclyAccessible", False)

        tags = self._normalize_tags(inst.get("TagList", []))

        risk_score = 0
        waste_reasons = []

        if is_public:
            risk_score += 50 # High risk
            waste_reasons.append("Publicly accessible database")

        return self._create_resource(
            id=db_id,
            name=db_id,
            rtype="rds_instance",
            creation_date=create_time,
            state=status,
            class_type=instance_class,
            tags=tags,
            risk_score=risk_score,
            waste_reasons=waste_reasons,
            optimizations=[{"type": "storage", "value": f"{allocated_storage}GB"}]
        )

    async def health_check(self) -> bool:
        try:
            def _check():
                session = boto3.Session(region_name=self.region)
                rds = session.client("rds")
                rds.describe_db_instances(MaxRecords=20)
                return True
            return await asyncio.to_thread(_check)
        except Exception:
            return False
