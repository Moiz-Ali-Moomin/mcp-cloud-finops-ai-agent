from ..base import BaseCollector
import google.auth
import google.auth.transport.requests
from typing import Optional

class GCPBaseCollector(BaseCollector):
    def __init__(self, project_id: Optional[str] = None, region: str = "global"):
        super().__init__("gcp", region)
        # Initialize project_id first to avoid AttributeError in later calls
        self.project_id = project_id
        
        # Load credentials and discover project if not provided
        self.credentials, discovered_project = google.auth.default()
        
        if not self.project_id:
            self.project_id = discovered_project

    def _resolve_project_id(self) -> str:
        # Minimal fallback if google.auth.default() didn't catch it
        # Real logic handled in __init__ via google.auth.default() usually
        return self.project_id or ""

    def _handle_gcp_error(self, operation: str, error: Exception):
        # Specific GCP error handling could go here
        self._handle_error(operation, error)
