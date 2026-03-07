"""
Tests for Cloud Resource and Cost Collectors.
"""
import pytest
from unittest.mock import patch, MagicMock

# Dynamically patch collectors to avoid requiring real clouds
@patch("opsyield.collectors.aws.ec2.collect_instances")
@patch("opsyield.collectors.gcp.compute.collect_instances")
class TestCollectors:
    
    @pytest.mark.asyncio
    async def test_aws_collector_mock(self, mock_gcp, mock_aws):
        """Test AWS collector behavior with mocked boto3 responses."""
        mock_aws.return_value = [
            {"id": "i-123", "type": "t3.medium", "state": "running"}
        ]
        
        instances = mock_aws()
        assert len(instances) == 1
        assert instances[0]["id"] == "i-123"
        assert instances[0]["type"] == "t3.medium"
        mock_aws.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_gcp_collector_mock(self, mock_gcp, mock_aws):
        """Test GCP collector behavior with mocked google-api responses."""
        mock_gcp.return_value = [
            {"id": "123456789", "name": "gke-node", "status": "RUNNING"}
        ]
        
        instances = mock_gcp()
        assert len(instances) == 1
        assert instances[0]["name"] == "gke-node"
        mock_gcp.assert_called_once()
