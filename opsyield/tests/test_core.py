"""
OpsYield Test Suite — Core Module Tests.

Covers:
    - Models (NormalizedCost, Resource, AnalysisResult)
    - Logging (get_logger, set_correlation_id, StructuredJSONFormatter, TimedOperation)
    - Aggregation (AggregationEngine)
    - Utils (retry, safe_get, safe_float, date helpers, chunk_list)
    - Snapshot (SnapshotManager)
"""

import json
import os
import time
import asyncio
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────

from opsyield.core.models import NormalizedCost, Resource, AnalysisResult


class TestNormalizedCost:
    def test_create_minimal(self):
        cost = NormalizedCost(
            provider="gcp",
            service="Compute",
            region="us-central1",
            resource_id="vm-123",
            cost=42.50,
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        assert cost.provider == "gcp"
        assert cost.cost == 42.50
        assert cost.tags == {}

    def test_create_with_all_fields(self):
        cost = NormalizedCost(
            provider="aws",
            service="EC2",
            region="us-east-1",
            resource_id="i-abc123",
            cost=100.0,
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            account_id="123456789",
            team="platform",
            business_unit="engineering",
            environment="production",
            tags={"Name": "web-server"},
        )
        assert cost.account_id == "123456789"
        assert cost.tags["Name"] == "web-server"
        assert cost.environment == "production"


class TestResource:
    def test_create_minimal(self):
        r = Resource(id="r-1", name="test-vm", type="vm", provider="gcp")
        assert r.id == "r-1"
        assert r.risk_score == 0
        assert r.dependencies == []

    def test_resource_with_metrics(self):
        r = Resource(
            id="i-abc",
            name="web-server",
            type="ec2_instance",
            provider="aws",
            state="RUNNING",
            cpu_avg=45.2,
            memory_avg=72.1,
            cost_30d=150.0,
        )
        assert r.state == "RUNNING"
        assert r.cpu_avg == 45.2
        assert r.cost_30d == 150.0


class TestAnalysisResult:
    def _make_result(self, **kwargs):
        defaults = {
            "meta": {"provider": "gcp"},
            "summary": {"total_cost": 100},
            "executive_summary": {"risk_score": 5},
            "trends": {},
            "daily_trends": [],
            "anomalies": [],
            "forecast": {},
            "governance_issues": [],
            "optimizations": [],
            "resources": [],
        }
        defaults.update(kwargs)
        return AnalysisResult(**defaults)

    def test_create_default(self):
        result = self._make_result()
        assert result.meta["provider"] == "gcp"
        assert result.running_count == 0
        assert result.waste_findings == []

    def test_with_enrichment(self):
        result = self._make_result(
            running_count=5,
            high_cost_resources=[{"id": "x", "cost": 500}],
        )
        assert result.running_count == 5
        assert len(result.high_cost_resources) == 1


# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

from opsyield.core.logging import (
    get_logger,
    set_correlation_id,
    get_correlation_id,
    StructuredJSONFormatter,
    TimedOperation,
)


class TestLogging:
    def test_get_logger_returns_logger(self):
        logger = get_logger("test_module")
        assert logger.name.startswith("opsyield")

    def test_get_logger_preserves_namespace(self):
        logger = get_logger("opsyield.core.test")
        assert logger.name == "opsyield.core.test"

    def test_correlation_id_lifecycle(self):
        cid = set_correlation_id("test-123")
        assert cid == "test-123"
        assert get_correlation_id() == "test-123"

    def test_correlation_id_auto_generate(self):
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 12

    def test_json_formatter_output(self):
        import logging

        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert "timestamp" in data

    def test_timed_operation_logs_duration(self):
        logger = get_logger("test_timer")
        with TimedOperation(logger, "test_op") as t:
            time.sleep(0.01)
        # No exception means success


# ─────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────

from opsyield.core.aggregation import AggregationEngine


class TestAggregationEngine:
    def _make_result(self, provider, cost, resources=None):
        return AnalysisResult(
            meta={"provider": provider},
            summary={"total_cost": cost, "total_waste": cost * 0.1, "resource_count": len(resources or [])},
            executive_summary={"risk_score": 5},
            trends={},
            daily_trends=[{"date": "2026-01-01", "amount": cost}],
            anomalies=[],
            forecast={"predicted_additional_spend": cost * 0.5},
            governance_issues=[],
            optimizations=[],
            resources=resources or [],
        )

    def test_empty_merge(self):
        engine = AggregationEngine()
        result = engine.merge([])
        assert result.summary["total_cost"] == 0

    def test_single_result_passthrough(self):
        engine = AggregationEngine()
        r = self._make_result("gcp", 100)
        result = engine.merge([r])
        assert result is r  # Should return same object

    def test_multi_provider_merge(self):
        engine = AggregationEngine()
        r1 = self._make_result("gcp", 100, [Resource(id="1", name="vm", type="vm", provider="gcp")])
        r2 = self._make_result("aws", 200, [Resource(id="2", name="ec2", type="ec2", provider="aws")])
        result = engine.merge([r1, r2])

        assert result.summary["total_cost"] == 300.0
        assert len(result.resources) == 2
        assert "gcp" in result.meta["provider"]
        assert "aws" in result.meta["provider"]

    def test_forecast_merge(self):
        engine = AggregationEngine()
        r1 = self._make_result("gcp", 100)
        r2 = self._make_result("aws", 200)
        result = engine.merge([r1, r2])

        assert result.forecast["predicted_additional_spend"] == 150.0  # 50 + 100
        assert result.forecast["source_forecasts"] == 2


# ─────────────────────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────────────────────

from opsyield.utils.helpers import (
    retry,
    utc_now,
    days_ago,
    date_range_str,
    iso_now,
    safe_get,
    safe_float,
    safe_round,
    chunk_list,
)


class TestDateHelpers:
    def test_utc_now_is_timezone_aware(self):
        now = utc_now()
        assert now.tzinfo is not None

    def test_days_ago(self):
        past = days_ago(7)
        assert (utc_now() - past).days == 7

    def test_date_range_str(self):
        start, end = date_range_str(30)
        assert len(start) == 10  # YYYY-MM-DD
        assert len(end) == 10

    def test_iso_now(self):
        result = iso_now()
        assert "T" in result


class TestSafeAccess:
    def test_safe_get_nested(self):
        data = {"a": {"b": {"c": 42}}}
        assert safe_get(data, "a", "b", "c") == 42

    def test_safe_get_missing(self):
        data = {"a": 1}
        assert safe_get(data, "x", "y", default=0) == 0

    def test_safe_get_list(self):
        data = {"items": [10, 20, 30]}
        assert safe_get(data, "items", 1) == 20

    def test_safe_float(self):
        assert safe_float("3.14") == 3.14
        assert safe_float(None, default=-1.0) == -1.0
        assert safe_float("not_a_number") == 0.0

    def test_safe_round(self):
        assert safe_round(3.14159, 2) == 3.14
        assert safe_round("bad") == 0.0


class TestChunkList:
    def test_basic_chunking(self):
        result = chunk_list([1, 2, 3, 4, 5], 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_empty_list(self):
        assert chunk_list([], 5) == []

    def test_exact_chunk(self):
        result = chunk_list([1, 2, 3, 4], 2)
        assert len(result) == 2


class TestRetry:
    def test_sync_retry_succeeds(self):
        call_count = 0

        @retry(max_attempts=3, delay_seconds=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    def test_sync_retry_exhausted(self):
        @retry(max_attempts=2, delay_seconds=0.01)
        def always_fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always_fail()

    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        call_count = 0

        @retry(max_attempts=3, delay_seconds=0.01)
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "done"

        result = await async_flaky()
        assert result == "done"
        assert call_count == 2


# ─────────────────────────────────────────────────────────────
# Snapshot
# ─────────────────────────────────────────────────────────────

from opsyield.core.snapshot import SnapshotManager, DiffResult


class TestSnapshotManager:
    def test_save_and_load(self, tmp_path):
        data = {"summary": {"total_cost": 100}, "version": 1}
        path = str(tmp_path / "snapshot.json")

        SnapshotManager.save(data, path)
        loaded = SnapshotManager.load(path)
        assert loaded["summary"]["total_cost"] == 100

    def test_compare_no_regression(self):
        baseline = {"summary": {"total_cost": 100}, "executive_summary": {"risk_score": 5}}
        current = {"summary": {"total_cost": 100}, "executive_summary": {"risk_score": 5}}

        result = SnapshotManager.compare(baseline, current)
        assert not result.is_regression
        assert result.cost_increase_pct == 0

    def test_compare_cost_regression(self):
        baseline = {"summary": {"total_cost": 100}, "executive_summary": {"risk_score": 5}}
        current = {"summary": {"total_cost": 150}, "executive_summary": {"risk_score": 5}}

        result = SnapshotManager.compare(baseline, current, cost_threshold_pct=10)
        assert result.is_regression
        assert result.cost_increase_pct == 50.0

    def test_compare_new_anomalies(self):
        baseline = {
            "summary": {"total_cost": 100},
            "executive_summary": {"risk_score": 5},
            "analytics": {"anomalies": [{"id": "a1"}]},
        }
        current = {
            "summary": {"total_cost": 100},
            "executive_summary": {"risk_score": 5},
            "analytics": {"anomalies": [{"id": "a1"}, {"id": "a2"}]},
        }

        result = SnapshotManager.compare(baseline, current)
        assert result.new_anomalies == 1


# ─────────────────────────────────────────────────────────────
# Interfaces
# ─────────────────────────────────────────────────────────────

from opsyield.core.interfaces import BaseProvider, OptimizationStrategy


class TestInterfaces:
    def test_base_provider_is_abstract(self):
        with pytest.raises(TypeError):
            BaseProvider()

    def test_optimization_strategy_is_abstract(self):
        with pytest.raises(TypeError):
            OptimizationStrategy()


# ─────────────────────────────────────────────────────────────
# Optimization Strategies
# ─────────────────────────────────────────────────────────────

from opsyield.optimization.strategies import IdleScorer, OptimizationEngine


class TestOptimizationStrategies:
    def test_idle_scorer_tagged_idle(self):
        cost = NormalizedCost(
            provider="aws", service="EC2", region="us-east-1",
            resource_id="i-1", cost=100, currency="USD",
            timestamp=datetime.now(timezone.utc),
            tags={"idle": "true"},
        )
        scorer = IdleScorer()
        result = scorer.analyze(cost)
        assert result is not None
        assert result["score"] == 100

    def test_idle_scorer_not_idle(self):
        cost = NormalizedCost(
            provider="aws", service="EC2", region="us-east-1",
            resource_id="i-1", cost=10, currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        scorer = IdleScorer()
        result = scorer.analyze(cost)
        assert result is None

    def test_optimization_engine_end_to_end(self):
        costs = [
            NormalizedCost(
                provider="aws", service="EC2", region="us-east-1",
                resource_id="i-idle", cost=100, currency="USD",
                timestamp=datetime.now(timezone.utc),
                tags={"idle": "true"},
            ),
            NormalizedCost(
                provider="gcp", service="Compute", region="us-central1",
                resource_id="vm-ok", cost=50, currency="USD",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        engine = OptimizationEngine()
        results = engine.analyze(costs)
        assert len(results) == 1
        assert results[0]["resource_id"] == "i-idle"


# ─────────────────────────────────────────────────────────────
# Intelligence Analytics
# ─────────────────────────────────────────────────────────────

from opsyield.intelligence.analytics import BudgetEngine, ForecastEngine


class TestIntelligenceAnalytics:
    def test_budget_under(self):
        engine = BudgetEngine()
        result = engine.check_budgets(current_spend=500, budget=1000)
        assert not result["is_over_budget"]

    def test_budget_over(self):
        engine = BudgetEngine()
        result = engine.check_budgets(current_spend=1500, budget=1000)
        assert result["is_over_budget"]

    def test_forecast_basic(self):
        engine = ForecastEngine()
        history = [{"amount": 100}, {"amount": 110}, {"amount": 105}]
        result = engine.forecast_spend(history, days_ahead=30)
        assert "predicted_additional_spend" in result or "predicted_total" in result

    def test_forecast_empty(self):
        engine = ForecastEngine()
        result = engine.forecast_spend([])
        assert result == {}
