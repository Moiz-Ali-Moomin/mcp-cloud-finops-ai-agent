import boto3
import asyncio
from typing import List, Dict, Any

from ..base import BaseCollector
from ...core.models import Resource

class S3Collector(BaseCollector):
    def __init__(self, region: str = "us-east-1"):
        super().__init__("aws", region)

    async def collect(self) -> List[Resource]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> List[Resource]:
        resources = []
        try:
            # S3 is global, but buckets have regions.
            # We list buckets and then check location if needed, 
            # or just list generic for now.
            session = boto3.Session(region_name=self.region)
            s3 = session.client("s3")
            
            response = s3.list_buckets()
            owner_id = response.get("Owner", {}).get("ID")

            for bucket in response.get("Buckets", []):
                try:
                    name = bucket.get("Name")
                    creation_date = bucket.get("CreationDate")
                    
                    # Fetching tags requires separate API call per bucket
                    # keeping it simple for discovery phase to avoid throttling
                    tags = {}
                    
                    # Risk Check: Public Access Block?
                    # This is expensive (GetPublicAccessBlock per bucket).
                    # We might want to do this in a "Deep Scan" mode or async queue.
                    # For now, just discovery.
                    
                    resources.append(self._create_resource(
                        id=name, # Bucket name is unique ID
                        name=name,
                        rtype="s3_bucket",
                        creation_date=creation_date,
                        tags=tags,
                        account_id=owner_id
                    ))

                except Exception as e:
                    self._handle_error(f"parse_bucket {bucket.get('Name')}", e)
                    continue

        except Exception as e:
            self._handle_error("collect_s3", e)
        
        return resources

    async def health_check(self) -> bool:
        try:
            def _check():
                session = boto3.Session(region_name=self.region)
                s3 = session.client("s3")
                s3.list_buckets()
                return True
            return await asyncio.to_thread(_check)
        except Exception:
            return False
