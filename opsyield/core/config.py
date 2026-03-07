"""
OpsYield Environment Configuration and Validation
"""
import os
from .logging import get_logger

logger = get_logger(__name__)

def validate_environment() -> None:
    """
    Validates that necessary environment variables are present on startup.
    Logs warnings if providers are missing required authentication material.
    """
    logger.info("Validating cloud environment configurations")

    # AWS Validation
    if not os.environ.get("AWS_ACCESS_KEY_ID") and not os.environ.get("AWS_PROFILE"):
        logger.warning(
            "AWS missing credentials",
            extra={"missing": ["AWS_ACCESS_KEY_ID", "AWS_PROFILE"], "provider": "aws"}
        )

    # GCP Validation
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning(
            "GCP Service Account missing",
            extra={"missing": ["GOOGLE_APPLICATION_CREDENTIALS"], "provider": "gcp"}
        )

    # Azure Validation
    azure_vars = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_SUBSCRIPTION_ID"
    ]
    missing_azure = [v for v in azure_vars if not os.environ.get(v)]
    if missing_azure:
        logger.warning(
            "Azure missing credentials",
            extra={"missing": missing_azure, "provider": "azure"}
        )

    logger.info("Environment configuration validation complete")
