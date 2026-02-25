"""
Shared CLI utilities for cloud provider status checks.

Extracted from individual provider modules to eliminate duplication.
Used by: gcp.py, aws.py, azure.py for subprocess-based CLI interactions.
"""

import json
import os
import subprocess
from typing import Dict, Any, Optional

from ..core.logging import get_logger

logger = get_logger(__name__)


def clean_env() -> dict:
    """Strip PAGER (breaks CLIs on Windows) and return env copy."""
    env = os.environ.copy()
    env.pop("PAGER", None)
    return env


def run_cli(cmd: str, timeout: int = 15, tag: str = "CLI") -> Dict[str, Any]:
    """
    Run a CLI command synchronously with full debug capture.

    Returns {ok, stdout, stderr, returncode} — never raises.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout,
            env=clean_env(),
        )
        logger.info(
            f"[{tag}] cmd={cmd!r} rc={result.returncode} "
            f"stdout={len(result.stdout)}B stderr={len(result.stderr)}B"
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.warning(f"[{tag}] Timeout: {cmd}")
        return {"ok": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as e:
        logger.error(f"[{tag}] Exception: {e}")
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}


def parse_json(raw: str) -> Optional[Any]:
    """Safely parse JSON, return None on failure."""
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None
