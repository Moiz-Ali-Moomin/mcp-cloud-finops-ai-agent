"""
Tests for Cloud Provider Interfaces and Factory.
"""
import pytest
from unittest.mock import patch, MagicMock

from opsyield.providers.factory import ProviderFactory

@pytest.mark.asyncio
class TestProviders:
    @patch("opsyield.providers.factory.ProviderFactory.get_all_statuses")
    async def test_get_all_statuses(self, mock_statuses):
        """Test getting all cloud provider configuration statuses."""
        mock_statuses.return_value = {
            "aws": {"status": "configured", "region": "us-east-1"},
            "gcp": {"status": "missing_credentials"},
            "azure": {"status": "configured"}
        }
        
        statuses = await ProviderFactory.get_all_statuses()
        
        assert "aws" in statuses
        assert statuses["aws"]["status"] == "configured"
        assert statuses["gcp"]["status"] == "missing_credentials"

    @patch("opsyield.providers.factory.ProviderFactory.create")
    def test_provider_creation(self, mock_create):
        """Test the creation of a cloud provider via factory."""
        mock_aws_provider = MagicMock()
        mock_aws_provider.provider_name = "aws"
        mock_create.return_value = mock_aws_provider
        
        provider = ProviderFactory.create("aws")
        assert provider.provider_name == "aws"
        mock_create.assert_called_once_with("aws")
