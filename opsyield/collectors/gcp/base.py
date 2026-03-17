from ..base import BaseCollector
from typing import Optional

class GCPBaseCollector(BaseCollector):
    def __init__(self, project_id: Optional[str] = None, region: str = "global"):
        super().__init__("gcp", region)
        self.project_id = project_id
        # Credentials are loaded lazily inside worker threads to avoid
        # blocking the asyncio event loop at construction time.
        self._credentials = None

    @property
    def credentials(self):
        """Lazy credential load — bypasses GCE metadata probe to avoid hangs."""
        if self._credentials is None:
            self._credentials = self._load_credentials()
        return self._credentials

    def _load_credentials(self):
        import json, os
        from google.auth.transport.requests import Request as GoogleAuthRequest

        # 1. Service account key file
        sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if sa_path and os.path.exists(sa_path):
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_file(
                sa_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        # 2. ADC authorized_user — load directly, no GCE metadata server needed
        adc_paths = [
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
            os.path.join(os.environ.get("APPDATA", ""), "gcloud", "application_default_credentials.json"),
        ]
        for adc_path in adc_paths:
            if os.path.exists(adc_path):
                try:
                    with open(adc_path) as f:
                        info = json.load(f)
                    if info.get("type") == "authorized_user":
                        from google.oauth2.credentials import Credentials
                        creds = Credentials(
                            token=None,
                            refresh_token=info["refresh_token"],
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=info["client_id"],
                            client_secret=info["client_secret"],
                        )
                        if not creds.valid:
                            creds.refresh(GoogleAuthRequest())
                        if not self.project_id:
                            self.project_id = info.get("quota_project_id")
                        return creds
                except Exception:
                    pass

        # 3. Fallback with GCE probe disabled
        os.environ.setdefault("NO_GCE_CHECK", "true")
        import google.auth
        creds, discovered_project = google.auth.default()
        if not creds.valid:
            creds.refresh(GoogleAuthRequest())
        if not self.project_id:
            self.project_id = discovered_project
        return creds

    def _resolve_project_id(self) -> str:
        return self.project_id or ""

    def _handle_gcp_error(self, operation: str, error: Exception):
        self._handle_error(operation, error)
