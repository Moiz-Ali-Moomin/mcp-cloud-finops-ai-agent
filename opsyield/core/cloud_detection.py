
import os
import shutil
import asyncio
from typing import Dict, Any

class CloudDetector:
    async def detect_all(self) -> Dict[str, Any]:
        """Detect installed CLIs and authentication status"""
        results = {
            "gcp": await self._check_gcp(),
            "aws": await self._check_aws(),
            "azure": await self._check_azure()
        }
        return results

    async def _check_gcp(self):
        installed = shutil.which("gcloud") is not None
        authenticated = False
        if installed:
            # Simple check, in reality would run 'gcloud auth list'
            authenticated = os.path.exists(os.path.expanduser("~/.config/gcloud/application_default_credentials.json")) or \
                            "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
        return {"installed": installed, "authenticated": authenticated}

    async def _check_aws(self):
        installed = shutil.which("aws") is not None
        authenticated = False
        if installed:
            authenticated = os.path.exists(os.path.expanduser("~/.aws/credentials")) or \
                            "AWS_ACCESS_KEY_ID" in os.environ
        return {"installed": installed, "authenticated": authenticated}

    async def _check_azure(self):
        installed = shutil.which("az") is not None
        authenticated = False
        if installed:
            # deeply simplified check
            authenticated = os.path.exists(os.path.expanduser("~/.azure/accessTokens.json"))
        return {"installed": installed, "authenticated": authenticated}
