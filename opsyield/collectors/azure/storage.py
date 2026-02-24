import asyncio
from typing import List
# azure-mgmt-storage is typically needed but wasn't in requirements.txt (only mgmt-resource, mgmt-compute, mgmt-costmanagement)
# Hmmm, user said "New Python libraries... will be added".
# But I can't run pip install. 
# I will use ResourceManagementClient to list generic resources of type 'Microsoft.Storage/storageAccounts'
# This is a safe fallback if specific SDK is missing.
from azure.mgmt.resource import ResourceManagementClient
from .base import AzureBaseCollector
from ...core.models import Resource

class AzureStorageCollector(AzureBaseCollector):
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            sub_id = self._get_subscription_id()
            client = ResourceManagementClient(self.credential, sub_id)
            
            # List storage accounts
            storage_accounts = client.resources.list(filter="resourceType eq 'Microsoft.Storage/storageAccounts'")

            for sa in storage_accounts:
                try:
                    resources.append(self._create_resource(
                        id=sa.id,
                        name=sa.name,
                        rtype="azure_storage_account",
                        region=sa.location,
                        subscription_id=sub_id,
                        tags=self._normalize_tags(sa.tags)
                    ))
                except Exception as e:
                    self._handle_error(f"parse_storage {sa.name}", e)

        except Exception as e:
            self._handle_error("collect_storage", e)
        
        return resources

    async def health_check(self) -> bool:
        try:
            sub_id = self._get_subscription_id()
            client = ResourceManagementClient(self.credential, sub_id)
            client.resources.list_top(1)
            return True
        except:
            return False
