import asyncio
from typing import List
from azure.mgmt.resource import ResourceManagementClient
from .base import AzureBaseCollector
from ...core.models import Resource

class AzureSQLCollector(AzureBaseCollector):
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            sub_id = self._get_subscription_id()
            client = ResourceManagementClient(self.credential, sub_id)
            
            # List SQL Servers
            sql_servers = client.resources.list(filter="resourceType eq 'Microsoft.Sql/servers'")

            for sql in sql_servers:
                try:
                    resources.append(self._create_resource(
                        id=sql.id,
                        name=sql.name,
                        rtype="azure_sql_server",
                        region=sql.location,
                        subscription_id=sub_id,
                        tags=self._normalize_tags(sql.tags)
                    ))
                except Exception as e:
                    self._handle_error(f"parse_sql {sql.name}", e)

        except Exception as e:
            self._handle_error("collect_sql", e)
        
        return resources

    async def health_check(self) -> bool:
        return True
