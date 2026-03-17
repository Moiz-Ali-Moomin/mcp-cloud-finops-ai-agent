import asyncio
from typing import List
from google.cloud import storage
from .base import GCPBaseCollector
from ...core.models import Resource
from ...core.logging import get_logger

logger = get_logger(__name__)


class GCPStorageCollector(GCPBaseCollector):
    async def collect(self) -> List[Resource]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._collect_sync),
                timeout=25.0
            )
        except asyncio.TimeoutError:
            logger.warning("[GCP Storage] Timed out after 25s, returning empty list")
            return []

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            if not self.project_id:
                return []

            client = storage.Client(
                project=self.project_id, credentials=self.credentials
            )
            buckets = client.list_buckets()

            for bucket in buckets:
                try:
                    resources.append(
                        self._create_resource(
                            id=bucket.name,
                            name=bucket.name,
                            rtype="gcp_storage_bucket",
                            creation_date=bucket.time_created,
                            region=bucket.location,
                            project_id=self.project_id,
                            tags=self._normalize_tags(bucket.labels),
                        )
                    )
                except Exception as e:
                    self._handle_error(f"parse_bucket {bucket.name}", e)

        except Exception as e:
            self._handle_error("collect_storage", e)

        return resources

    async def health_check(self) -> bool:
        try:
            _ = storage.Client(project=self.project_id, credentials=self.credentials)
            return True
        except Exception:
            return False
