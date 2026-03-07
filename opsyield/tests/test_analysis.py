"""
Tests for FinOps Analysis Engine.
"""

import pytest
from unittest.mock import MagicMock

from opsyield.analysis.waste_detector import analyze_waste
from opsyield.core.models import Resource


class TestAnalysisEngine:
    def test_waste_detector_idle_compute(self):
        """Test that the waste detector flags idle resources."""
        idle_resource = Resource(
            id="i-idle123",
            name="forgotten-server",
            type="compute",
            provider="aws",
            state="RUNNING",
            cpu_avg=1.5,  # Very low CPU
            memory_avg=10.0,
            cost_30d=150.0,
        )

        active_resource = Resource(
            id="i-active456",
            name="prod-db",
            type="compute",
            provider="aws",
            state="RUNNING",
            cpu_avg=65.0,  # High CPU
            memory_avg=80.0,
            cost_30d=450.0,
        )

        # Test detection logic
        findings = analyze_waste([idle_resource, active_resource])

        # Should only flag the idle resource
        assert len(findings) == 1
        assert findings[0]["resource_id"] == "i-idle123"
        assert findings[0]["reason"] == "Low CPU utilization (< 5%)"

    def test_waste_detector_unattached_volumes(self):
        """Test detection of unattached disks."""
        unattached_disk = Resource(
            id="vol-0123",
            name="old-backup",
            type="disk",
            provider="aws",
            state="AVAILABLE",  # Available but not in-use
            cost_30d=25.0,
        )

        findings = analyze_waste([unattached_disk])
        assert len(findings) == 1
        assert "unattached" in findings[0]["reason"].lower()
