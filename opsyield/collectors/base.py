from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.logging import get_logger
from ..core.models import Resource

logger = get_logger(__name__)

class BaseCollector(ABC):
    """
    Abstract base class for all cloud resource collectors.
    Enforces a common interface for discovery, validation, and error handling.
    """
    def __init__(self, provider: str, region: str = "global"):
        self.provider = provider
        self.region = region
    
    @abstractmethod
    async def collect(self) -> List[Resource]:
        """
        Main entry point to discover resources.
        Must return a list of unified Resource objects.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Quick check to verify credentials and API access.
        """
        pass

    def _normalize_tags(self, tags: Any) -> Dict[str, str]:
        """
        Helper to normalize tags to a flat Dict[str, str].
        Handles various cloud provider tag formats (list of dicts, etc.)
        """
        if isinstance(tags, dict):
            return {str(k): str(v) for k, v in tags.items()}
        elif isinstance(tags, list):
            # AWS format: [{'Key': 'Name', 'Value': 'MyInstance'}]
            normalized = {}
            for t in tags:
                if isinstance(t, dict) and "Key" in t and "Value" in t:
                    normalized[str(t["Key"])] = str(t["Value"])
            return normalized
        return {}

    def _handle_error(self, operation: str, error: Exception) -> None:
        """
        Standardized error logging.
        """
        logger.error(f"[{self.provider.upper()}] Error during {operation}: {str(error)}")

    def _create_resource(self, 
                         id: str, 
                         name: str, 
                         rtype: str, 
                         **kwargs) -> Resource:
        """
        Factory method to create a unified Resource object with defaults.
        """
        return Resource(
            id=id,
            name=name or id,
            type=rtype,
            provider=self.provider,
            region=self.region,
            last_seen=datetime.utcnow(),
            **kwargs
        )
