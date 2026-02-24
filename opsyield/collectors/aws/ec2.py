import boto3
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from ..base import BaseCollector
from ...core.models import Resource

class EC2Collector(BaseCollector):
    def __init__(self, region: str = "us-east-1"):
        super().__init__("aws", region)
    
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            session = boto3.Session(region_name=self.region)
            ec2 = session.client("ec2")
            paginator = ec2.get_paginator("describe_instances")

            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        try:
                            r = self._parse_instance(inst)
                            resources.append(r)
                        except Exception as e:
                            self._handle_error(f"parse_instance {inst.get('InstanceId')}", e)
                            continue
        except Exception as e:
            self._handle_error("collect_ec2", e)
        
        return resources

    def _parse_instance(self, inst: Dict[str, Any]) -> Resource:
        instance_id = inst.get("InstanceId", "")
        instance_type = inst.get("InstanceType", "unknown")
        state = (inst.get("State") or {}).get("Name", "unknown")
        launch_time = inst.get("LaunchTime")
        
        tags = self._normalize_tags(inst.get("Tags", []))
        name = tags.get("Name", instance_id)
        
        public_ip = inst.get("PublicIpAddress")
        
        # Calculate scores (logic can be expanded)
        risk_score = 0
        if public_ip and state == "running":
            # Heuristic: Public IP on non-web/lb might be risky, specialized logic elsewhere
            pass

        # Dependencies
        deps = []
        # Block Device Mappings (EBS)
        for bdm in inst.get("BlockDeviceMappings", []):
            ebs = bdm.get("Ebs", {})
            vol_id = ebs.get("VolumeId")
            if vol_id:
                deps.append(vol_id)
                
        # Security Groups
        for sg in inst.get("SecurityGroups", []):
            sg_id = sg.get("GroupId")
            if sg_id:
                deps.append(sg_id)

        # VPC / Subnet
        vpc_id = inst.get("VpcId")
        if vpc_id:
            deps.append(vpc_id)
        subnet_id = inst.get("SubnetId")
        if subnet_id:
            deps.append(subnet_id)

        return self._create_resource(
            id=instance_id,
            name=name,
            rtype="ec2_instance",
            creation_date=launch_time,
            state=state,
            class_type=instance_type,
            external_ip=public_ip,
            tags=tags,
            risk_score=risk_score,
            dependencies=deps
        )

    async def health_check(self) -> bool:
        try:
            def _check():
                session = boto3.Session(region_name=self.region)
                ec2 = session.client("ec2")
                ec2.describe_instances(MaxResults=5)
                return True
            
            return await asyncio.to_thread(_check)
        except Exception as e:
            self._handle_error("health_check", e)
            return False
