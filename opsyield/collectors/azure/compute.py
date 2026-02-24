import asyncio
from typing import List
from azure.mgmt.compute import ComputeManagementClient
from .base import AzureBaseCollector
from ...core.models import Resource

class AzureComputeCollector(AzureBaseCollector):
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            sub_id = self._get_subscription_id()
            client = ComputeManagementClient(self.credential, sub_id)
            
            # List all VMs in subscription
            vms = client.virtual_machines.list_all()

            for vm in vms:
                try:
                    resources.append(self._parse_vm(vm, sub_id))
                except Exception as e:
                    self._handle_error(f"parse_vm {vm.name}", e)
                    
        except Exception as e:
            self._handle_error("collect_compute", e)
        
        return resources

    def _parse_vm(self, vm, sub_id) -> Resource:
        vm_id = vm.id
        name = vm.name
        location = vm.location
        vm_size = vm.hardware_profile.vm_size if vm.hardware_profile else "unknown"
        
        # Power state requires an instance view call (skip for discovery speed, or add if needed)
        # For now, simplistic discovery.
        
        tags = self._normalize_tags(vm.tags)
        
        return self._create_resource(
            id=vm_id,
            name=name,
            rtype="azure_vm",
            region=location,
            class_type=vm_size,
            subscription_id=sub_id,
            tags=tags
        )

    async def health_check(self) -> bool:
        try:
            sub_id = self._get_subscription_id()
            client = ComputeManagementClient(self.credential, sub_id)
            client.virtual_machines.list(max_results=1) # Verify access
            return True
        except:
            return False
