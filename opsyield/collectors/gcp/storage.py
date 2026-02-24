import asyncio
from typing import List
from google.cloud import storage
from .base import GCPBaseCollector
from ...core.models import Resource

class GCPStorageCollector(GCPBaseCollector):
    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            if not self.project_id:
                return []
            
            client = storage.Client(project=self.project_id, credentials=self.credentials)
            buckets = client.list_buckets()

            for bucket in buckets:
                try:
                    resources.append(self._create_resource(
                        id=bucket.name,
                        name=bucket.name,
                        rtype="gcp_storage_bucket",
                        creation_date=bucket.time_created,
                        region=bucket.location,
                        project_id=self.project_id,
                        tags=self._normalize_tags(bucket.labels)
                    ))
                except Exception as e:
                    self._handle_error(f"parse_bucket {bucket.name}", e)

        except Exception as e:
            self._handle_error("collect_storage", e)
        
        return resources

    async def health_check(self) -> bool:
        try:
            client = storage.Client(project=self.project_id, credentials=self.credentials)
            return True
        except:
            return False
