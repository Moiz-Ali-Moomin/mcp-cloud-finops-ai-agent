import asyncio
from typing import List
from datetime import datetime
from google.cloud import compute_v1
from .base import GCPBaseCollector
from ...core.models import Resource

class GCPComputeCollector(GCPBaseCollector):
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            if not self.project_id:
                raise ValueError("No project_id found")

            client = compute_v1.InstancesClient(credentials=self.credentials)
            request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
            
            # Aggregated list returns a generator, iterating it triggers API calls
            for zone, response in client.aggregated_list(request=request):
                if response.instances:
                    for instance in response.instances:
                         try:
                             resources.append(self._parse_instance(instance))
                         except Exception as e:
                             self._handle_error(f"parse_instance {instance.name}", e)

        except Exception as e:
            self._handle_error("collect_compute", e)
        
        return resources

    def _parse_instance(self, inst) -> Resource:
        instance_id = str(inst.id)
        name = inst.name
        status = inst.status
        machine_type = inst.machine_type.split('/')[-1] if inst.machine_type else "unknown"
        creation_ts = inst.creation_timestamp
        
        # Parse timestamp
        # GCP gives ISO like '2023-01-01T00:00:00.000-07:00'
        # Simplified parsing
        created_dt = None
        if creation_ts:
            try:
                created_dt = datetime.fromisoformat(creation_ts) # Requires recent Python for full ISO
            except:
                pass

        # Network Interfaces for IP
        external_ip = None
        if inst.network_interfaces:
            for ni in inst.network_interfaces:
                if ni.access_configs:
                    for ac in ni.access_configs:
                        if ac.nat_i_p:
                            external_ip = ac.nat_i_p
                            break

        return self._create_resource(
            id=instance_id,
            name=name,
            rtype="gcp_compute_instance",
            creation_date=created_dt,
            state=status,
            class_type=machine_type,
            external_ip=external_ip,
            project_id=self.project_id,
            tags={"labels": str(inst.labels)} # Flatten labels?
        )

    async def health_check(self) -> bool:
        try:
            client = compute_v1.InstancesClient(credentials=self.credentials)
            # Just verify client creation and project
            return True
        except:
            return False
