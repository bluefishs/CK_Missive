"""
ToolSuccessMonitor 單元測試

測試工具成功率監控邏輯（不依賴 Redis）:
- ToolStats 資料結構
- 成功率計算
- 降級策略邏輯
"""

from unittest.mock import patch, AsyncMock

import pytest
from app.services.ai.agent.agent_tool_monitor import ToolStats, ToolSuccessMonitor


class TestToolStats:
    """ToolStats 資料結構"""

    def test_overall_success_rate_no_calls(self):
        stats = ToolStats(tool_name="search_documents")
        assert stats.overall_success_rate == 1.0

    def test_overall_success_rate_all_success(self):
        stats = ToolStats(tool_name="test", total_calls=10, success_count=10)
        assert stats.overall_success_rate == 1.0

    def test_overall_success_rate_mixed(self):
        stats = ToolStats(tool_name="test", total_calls=10, success_count=7, failure_count=3)
        assert stats.overall_success_rate == 0.7

    def test_overall_success_rate_all_failed(self):
        stats = ToolStats(tool_name="test", total_calls=5, success_count=0, failure_count=5)
        assert stats.overall_success_rate == 0.0

    def test_default_not_degraded(self):
        stats = ToolStats(tool_name="test")
        assert stats.is_degraded is False

    def test_default_values(self):
        stats = ToolStats(tool_name="test_tool")
        assert stats.total_calls == 0
        assert stats.avg_latency_ms == 0.0
        assert stats.avg_result_count == 0.0
        assert stats.recent_success_rate == 1.0


class TestToolSuccessMonitorInit:
    """ToolSuccessMonitor 初始化與降級邏輯"""

    def test_default_init(self):
        monitor = ToolSuccessMonitor()
        assert monitor._window_size == 100
        assert monitor._degraded_threshold == 0.3
        assert monitor._recovery_threshold == 0.7

    def test_custom_init(self):
        monitor = ToolSuccessMonitor(
            window_size=50,
            degraded_threshold=0.2,
            recovery_threshold=0.6,
            probe_interval=300,
        )
        assert monitor._window_size == 50
        assert monitor._degraded_threshold == 0.2
        assert monitor._recovery_threshold == 0.6
        assert monitor._probe_interval == 300

    @pytest.mark.asyncio
    async def test_get_stats_no_redis_returns_default(self):
        monitor = ToolSuccessMonitor()
        stats = await monitor.get_stats("nonexistent_tool")
        assert stats.tool_name == "nonexistent_tool"
        assert stats.total_calls == 0

    @pytest.mark.asyncio
    async def test_is_degraded_no_redis_returns_false(self):
        monitor = ToolSuccessMonitor()
        assert await monitor.is_degraded("search_documents") is False

    @pytest.mark.asyncio
    async def test_get_degraded_tools_no_redis_returns_empty(self):
        monitor = ToolSuccessMonitor()
        with patch.object(monitor, '_get_redis', new_callable=AsyncMock, return_value=None):
            assert await monitor.get_degraded_tools() == set()

    @pytest.mark.asyncio
    async def test_get_all_stats_returns_dict(self):
        monitor = ToolSuccessMonitor()
        result = await monitor.get_all_stats()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_record_does_not_raise(self):
        monitor = ToolSuccessMonitor()
        # Should not raise regardless of Redis availability
        await monitor.record("test_tool_unit", True, 100.0, 5)
